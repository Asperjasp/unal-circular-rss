#!/bin/bash
# ==============================================================================
# Health Scraper - Quick Start Script
# ==============================================================================
# This script sets up and runs the Health Scraper locally.
# 
# Prerequisites:
#   - Conda installed (Miniconda or Anaconda)
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏥 Health Institutions Scraper${NC}"
echo "======================================"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ Conda is not installed. Please install Miniconda or Anaconda first.${NC}"
    echo "   Visit: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check if environment exists
if ! conda env list | grep -q "health-scraper"; then
    echo -e "${YELLOW}📦 Creating conda environment...${NC}"
    conda env create -f environment.yml
fi

# Activate environment
echo -e "${GREEN}🔄 Activating environment...${NC}"
eval "$(conda shell.bash hook)"
conda activate health-scraper

# Run the application
echo -e "${GREEN}🚀 Starting the server...${NC}"
echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "📱 ${GREEN}Frontend:${NC} http://localhost:8000"
echo -e "📚 ${GREEN}API Docs:${NC} http://localhost:8000/docs"
echo -e "❤️  ${GREEN}Health:${NC}   http://localhost:8000/health"
echo -e "${BLUE}=================================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

python main.py
