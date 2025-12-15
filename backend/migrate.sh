#!/bin/bash
# Alembic migration helper script for Docker

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Alembic Migration Helper${NC}"
echo "=========================="
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found. Trying 'docker compose'..."
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Get the service name (default to 'api')
SERVICE_NAME=${1:-api}

case "$2" in
    current)
        echo "Checking current migration status..."
        $DOCKER_COMPOSE exec $SERVICE_NAME alembic current
        ;;
    upgrade)
        echo "Running migrations..."
        $DOCKER_COMPOSE exec $SERVICE_NAME alembic upgrade head
        ;;
    downgrade)
        echo "Rolling back one migration..."
        $DOCKER_COMPOSE exec $SERVICE_NAME alembic downgrade -1
        ;;
    history)
        echo "Migration history:"
        $DOCKER_COMPOSE exec $SERVICE_NAME alembic history
        ;;
    revision)
        if [ -z "$3" ]; then
            echo "Error: Please provide a migration message"
            echo "Usage: ./migrate.sh api revision 'migration message'"
            exit 1
        fi
        echo "Creating new migration..."
        $DOCKER_COMPOSE exec $SERVICE_NAME alembic revision --autogenerate -m "$3"
        ;;
    *)
        echo "Usage: ./migrate.sh [service] [command] [options]"
        echo ""
        echo "Commands:"
        echo "  current              - Show current migration version"
        echo "  upgrade              - Apply all pending migrations"
        echo "  downgrade            - Rollback one migration"
        echo "  history              - Show migration history"
        echo "  revision 'message'    - Create new migration (autogenerate)"
        echo ""
        echo "Examples:"
        echo "  ./migrate.sh api current"
        echo "  ./migrate.sh api upgrade"
        echo "  ./migrate.sh api revision 'add new column'"
        exit 1
        ;;
esac

