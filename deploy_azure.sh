#!/usr/bin/env bash
# ============================================
# Azure Deployment Script for Health Scraper
# ============================================
# 
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed
#
# Usage:
#   chmod +x deploy_azure.sh
#   ./deploy_azure.sh
# ============================================

set -e

# Configuration - CHANGE THESE VALUES
RESOURCE_GROUP="health-scraper-rg"
LOCATION="eastus"  # Azure region
ACR_NAME="healthscraperacr"  # Azure Container Registry name (must be unique, lowercase, no dashes)
APP_NAME="health-scraper-app"
CONTAINER_APP_ENV="health-scraper-env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Health Scraper - Azure Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed.${NC}"
    echo "Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
echo -e "${YELLOW}Checking Azure login status...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Please log in to Azure:${NC}"
    az login
fi

echo -e "${GREEN}✓ Logged in to Azure${NC}"
SUBSCRIPTION=$(az account show --query name -o tsv)
echo "  Using subscription: $SUBSCRIPTION"

# Create Resource Group
echo -e "\n${YELLOW}Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION --output none
echo -e "${GREEN}✓ Resource group '$RESOURCE_GROUP' created${NC}"

# Create Azure Container Registry
echo -e "\n${YELLOW}Creating Azure Container Registry...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true \
    --output none
echo -e "${GREEN}✓ Container Registry '$ACR_NAME' created${NC}"

# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Build and push Docker image
echo -e "\n${YELLOW}Building and pushing Docker image...${NC}"
az acr build \
    --registry $ACR_NAME \
    --image health-scraper:latest \
    --file Dockerfile \
    .
echo -e "${GREEN}✓ Docker image built and pushed${NC}"

# Create Container Apps Environment
echo -e "\n${YELLOW}Creating Container Apps Environment...${NC}"
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --output none
echo -e "${GREEN}✓ Container Apps Environment created${NC}"

# Deploy Container App
echo -e "\n${YELLOW}Deploying Container App...${NC}"
az containerapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image "$ACR_LOGIN_SERVER/health-scraper:latest" \
    --target-port 8000 \
    --ingress external \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --cpu 1 \
    --memory 2Gi \
    --min-replicas 0 \
    --max-replicas 3 \
    --env-vars "DATABASE_URL=sqlite:///./data/health_institutions.db" \
    --output none
echo -e "${GREEN}✓ Container App deployed${NC}"

# Get the app URL
APP_URL=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Application URL: ${GREEN}https://$APP_URL${NC}"
echo -e "API Documentation: ${GREEN}https://$APP_URL/docs${NC}"
echo -e "Frontend: ${GREEN}https://$APP_URL/${NC}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:    az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo "  Scale app:    az containerapp update --name $APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 1 --max-replicas 5"
echo "  Delete all:   az group delete --name $RESOURCE_GROUP --yes"
echo ""
