#!/bin/bash
# ==============================================================================
# Azure Deployment Script for Health Institutions Scraper
# ==============================================================================
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed (for local build testing)
#
# Usage:
#   chmod +x azure-deploy.sh
#   ./azure-deploy.sh
# ==============================================================================

# Configuration - EDIT THESE VALUES
RESOURCE_GROUP="health-scraper-rg"
LOCATION="eastus"  # Change to your preferred Azure region
APP_NAME="health-scraper-api"
ACR_NAME="healthscraperacr"  # Must be globally unique, lowercase, alphanumeric only
CONTAINER_APP_ENV="health-scraper-env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏥 Health Institutions Scraper - Azure Deployment${NC}"
echo "=================================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    echo "   Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
az account show &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Running 'az login'...${NC}"
    az login
fi

echo -e "\n${GREEN}1. Creating Resource Group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION

echo -e "\n${GREEN}2. Creating Azure Container Registry...${NC}"
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

echo -e "\n${GREEN}3. Building and pushing Docker image...${NC}"
az acr build --registry $ACR_NAME --image $APP_NAME:latest .

echo -e "\n${GREEN}4. Creating Container Apps Environment...${NC}"
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION

echo -e "\n${GREEN}5. Deploying Container App...${NC}"
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

az containerapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image "$ACR_NAME.azurecr.io/$APP_NAME:latest" \
    --target-port 8000 \
    --ingress 'external' \
    --registry-server "$ACR_NAME.azurecr.io" \
    --registry-username $ACR_NAME \
    --registry-password $ACR_PASSWORD \
    --cpu 1 \
    --memory 2Gi \
    --min-replicas 0 \
    --max-replicas 3 \
    --env-vars "DATABASE_URL=sqlite:///data/health_institutions.db"

echo -e "\n${GREEN}6. Getting application URL...${NC}"
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)

echo -e "\n${GREEN}✅ Deployment Complete!${NC}"
echo "=================================================="
echo -e "🌐 API URL: ${YELLOW}https://$APP_URL${NC}"
echo -e "📚 API Docs: ${YELLOW}https://$APP_URL/docs${NC}"
echo -e "🖥️  Frontend: ${YELLOW}https://$APP_URL/${NC}"
echo ""
echo "To update the deployment, run:"
echo "  az acr build --registry $ACR_NAME --image $APP_NAME:latest ."
echo "  az containerapp update --name $APP_NAME --resource-group $RESOURCE_GROUP --image $ACR_NAME.azurecr.io/$APP_NAME:latest"
