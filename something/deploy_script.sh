#!/bin/bash

# deploy.sh - Deployment script for MSK EKS pub/sub system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
ECR_REPOSITORY=${ECR_REPOSITORY:-msk-pubsub-app}
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME:-my-eks-cluster}
NAMESPACE=${NAMESPACE:-default}

echo -e "${GREEN}🚀 MSK EKS Pub/Sub Deployment Script${NC}"
echo "=================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check if required tools are installed
    command -v aws >/dev/null 2>&1 || { print_error "AWS CLI is required but not installed. Aborting."; exit 1; }
    command -v cdk >/dev/null 2>&1 || { print_error "AWS CDK is required but not installed. Aborting."; exit 1; }
    command -v kubectl >/dev/null 2>&1 || { print_error "kubectl is required but not installed. Aborting."; exit 1; }
    command -v docker >/dev/null 2>&1 || { print_error "Docker is required but not installed. Aborting."; exit 1; }

    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi

    # Get AWS account ID if not provided
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        print_status "Detected AWS Account ID: $AWS_ACCOUNT_ID"
    fi

    print_status "Prerequisites check passed ✓"
}

# Deploy CDK stack
deploy_cdk_stack() {
    print_status "Deploying MSK CDK stack..."

    # Install CDK dependencies
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt
    fi

    # Bootstrap CDK (if not already done)
    print_status "Bootstrapping CDK..."
    cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

    # Deploy the stack
    print_status "Deploying CDK stack..."
    cdk deploy MSKEKSPubSubStack --require-approval never

    print_status "CDK stack deployed successfully ✓"
}

# Build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."

    # Create ECR repository if it doesn't exist
    if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION >/dev/null 2>&1; then
        print_status "Creating ECR repository: $ECR_REPOSITORY"
        aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    fi

    # Get ECR login token
    print_status "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    # Build Docker image
    print_status "Building Docker image..."
    docker build -t $ECR_REPOSITORY .

    # Tag and push image
    IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
    docker tag $ECR_REPOSITORY:latest $IMAGE_URI

    print_status "Pushing image to ECR..."
    docker push $IMAGE_URI

    print_status "Docker image built and pushed successfully ✓"
    echo "Image URI: $IMAGE_URI"
}

# Update Kubernetes manifests
update_k8s_manifests() {
    print_status "Updating Kubernetes manifests..."

    # Get MSK role ARN from CDK outputs
    MSK_ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name MSKEKSPubSubStack \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`EKSMSKRoleArn`].OutputValue' \
        --output text)

    if [ -z "$MSK_ROLE_ARN" ]; then
        print_error "Could not retrieve MSK role ARN from CDK stack"
        exit 1
    fi

    print_status "MSK Role ARN: $MSK_ROLE_ARN"

    # Update the ServiceAccount with the correct role ARN
    sed -i.bak "s|arn:aws:iam::ACCOUNT_ID:role/EKSMSKRole|$MSK_ROLE_ARN|g" k8s-deployment.yaml

    # Update the image URI in deployment
    sed -i.bak "s|your-registry/msk-pubsub-app:latest|$IMAGE_URI|g" k8s-deployment.yaml

    print_status "Kubernetes manifests updated ✓"
}

# Deploy to EKS
deploy_to_eks() {
    print_status "Deploying to EKS cluster: $EKS_CLUSTER_NAME"

    # Update kubeconfig
    print_status "Updating kubeconfig..."
    aws eks update-kubeconfig --region $AWS_REGION --name $EKS_CLUSTER_NAME

    # Apply Kubernetes manifests
    print_status "Applying Kubernetes manifests..."
    kubectl apply -f k8s-deployment.yaml -n $NAMESPACE

    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl rollout status deployment/msk-pubsub-app -n $NAMESPACE --timeout=300s

    print_status "EKS deployment completed successfully ✓"
}

# Get deployment status
get_deployment_status() {
    print_status "Getting deployment status..."

    echo ""
    echo "=== MSK Cluster Information ==="
    aws cloudformation describe-stacks \
        --stack-name MSKEKSPubSubStack \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`MSKClusterArn`].OutputValue' \
        --output text

    echo ""
    echo "=== Kubernetes Pods ==="
    kubectl get pods -l app=msk-pubsub-app -n $NAMESPACE

    echo ""
    echo "=== Kubernetes Services ==="
    kubectl get svc msk-pubsub-service -n $NAMESPACE

    echo ""
    echo "=== Application Logs (last 20 lines) ==="
    kubectl logs -l app=msk-pubsub-app -n $NAMESPACE --tail=20
}

# Test the deployment
test_deployment() {
    print_status "Testing the deployment..."

    # Port forward to test locally
    print_status "Setting up port forwarding..."
    kubectl port-forward svc/msk-pubsub-service 8080:80 -n $NAMESPACE &
    PORT_FORWARD_PID=$!

    # Wait for port forward to be ready
    sleep 5

    # Test health endpoint
    if curl -f http://localhost:8080/health >/dev/null 2>&1; then
        print_status "Health check passed ✓"

        # Test publish endpoint
        print_status "Testing message publishing..."
        curl -X POST http://localhost:8080/publish \
            -H "Content-Type: application/json" \
            -d '{"topic": "user-events", "message": {"test": "deployment"}, "key": "test-key"}' \
            && print_status "Message publishing test passed ✓"
    else
        print_error "Health check failed"
    fi

    # Clean up port forward
    kill $PORT_FORWARD_PID 2>/dev/null || true
}

# Cleanup function
cleanup() {
    print_status "Cleaning up temporary files..."
    rm -f k8s-deployment.yaml.bak
}

# Main deployment function
main() {
    case "${1:-all}" in
        "prerequisites")
            check_prerequisites
            ;;
        "cdk")
            check_prerequisites
            deploy_cdk_stack
            ;;
        "image")
            check_prerequisites
            build_and_push_image
            ;;
        "k8s")
            check_prerequisites
            update_k8s_manifests
            deploy_to_eks
            ;;
        "status")
            get_deployment_status
            ;;
        "test")
            test_deployment
            ;;
        "all")
            check_prerequisites
            deploy_cdk_stack
            build_and_push_image
            update_k8s_manifests
            deploy_to_eks
            get_deployment_status
            cleanup
            print_status "🎉 Deployment completed successfully!"
            print_status "You can now test your MSK pub/sub system."
            ;;
        *)
            echo "Usage: $0 {prerequisites|cdk|image|k8s|status|test|all}"
            echo ""
            echo "Commands:"
            echo "  prerequisites - Check if all required tools are installed"
            echo "  cdk          - Deploy the MSK CDK stack"
            echo "  image        - Build and push Docker image to ECR"
            echo "  k8s          - Deploy to EKS cluster"
            echo "  status       - Get deployment status"
            echo "  test         - Test the deployment"
            echo "  all          - Run complete deployment (default)"
            exit 1
            ;;
    esac
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"