#!/bin/bash
# Real-time resource monitoring for OctoLLM on Unraid
# Monitors CPU, RAM, GPU, disk, and network usage

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
LOG_DIR="/mnt/user/appdata/octollm/logs"
LOG_FILE="$LOG_DIR/resource-monitor.log"
mkdir -p "$LOG_DIR"

log_entry() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Alert thresholds
CPU_WARN=80
CPU_CRIT=90
MEM_WARN=85
MEM_CRIT=95
GPU_TEMP_WARN=80
GPU_TEMP_CRIT=90
DISK_WARN=90

clear

echo "============================================================================"
echo "  OctoLLM Resource Monitor - Dell PowerEdge R730xd"
echo "============================================================================"
echo ""

while true; do
    # System info
    HOSTNAME=$(hostname)
    UPTIME=$(uptime -p)

    # CPU
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    CPU_CORES=$(nproc)

    # Memory
    MEM_TOTAL=$(free -g | awk '/^Mem:/{print $2}')
    MEM_USED=$(free -g | awk '/^Mem:/{print $3}')
    MEM_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED/$MEM_TOTAL)*100}")

    # GPU (if available)
    if command -v nvidia-smi &> /dev/null; then
        GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
        GPU_MEM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
        GPU_MEM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
        GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
        GPU_POWER=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader)
        GPU_MEM_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($GPU_MEM_USED/$GPU_MEM_TOTAL)*100}")
        GPU_AVAILABLE=true
    else
        GPU_AVAILABLE=false
    fi

    # Disk
    DISK_TOTAL=$(df -BG /mnt/user | awk 'NR==2 {print $2}' | tr -d 'G')
    DISK_USED=$(df -BG /mnt/user | awk 'NR==2 {print $3}' | tr -d 'G')
    DISK_PERCENT=$(df /mnt/user | awk 'NR==2 {print $5}' | tr -d '%')

    # Network
    RX_BYTES=$(cat /sys/class/net/bond0/statistics/rx_bytes 2>/dev/null || echo "0")
    TX_BYTES=$(cat /sys/class/net/bond0/statistics/tx_bytes 2>/dev/null || echo "0")
    sleep 1
    RX_BYTES_NEW=$(cat /sys/class/net/bond0/statistics/rx_bytes 2>/dev/null || echo "0")
    TX_BYTES_NEW=$(cat /sys/class/net/bond0/statistics/tx_bytes 2>/dev/null || echo "0")
    RX_RATE=$(( ($RX_BYTES_NEW - $RX_BYTES) / 1024 / 1024 ))
    TX_RATE=$(( ($TX_BYTES_NEW - $TX_BYTES) / 1024 / 1024 ))

    # Clear screen and display
    tput cup 0 0

    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║  OctoLLM Resource Monitor - $HOSTNAME"
    echo "║  Uptime: $UPTIME"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo ""

    # CPU
    printf "CPU (${CPU_CORES} cores): "
    if (( $(echo "$CPU_USAGE > $CPU_CRIT" | bc -l) )); then
        printf "${RED}%.1f%%${NC} [CRITICAL]\n" "$CPU_USAGE"
        log_entry "ALERT: CPU usage critical: ${CPU_USAGE}%"
    elif (( $(echo "$CPU_USAGE > $CPU_WARN" | bc -l) )); then
        printf "${YELLOW}%.1f%%${NC} [WARNING]\n" "$CPU_USAGE"
    else
        printf "${GREEN}%.1f%%${NC}\n" "$CPU_USAGE"
    fi

    # Progress bar for CPU
    printf "["
    FILLED=$(awk "BEGIN {printf \"%.0f\", $CPU_USAGE/2}")
    for ((i=0; i<50; i++)); do
        if [ $i -lt $FILLED ]; then printf "█"; else printf "░"; fi
    done
    printf "]\n\n"

    # Memory
    printf "RAM (${MEM_TOTAL}GB): "
    if (( $(echo "$MEM_PERCENT > $MEM_CRIT" | bc -l) )); then
        printf "${RED}${MEM_USED}GB / ${MEM_TOTAL}GB (${MEM_PERCENT}%%)${NC} [CRITICAL]\n"
        log_entry "ALERT: Memory usage critical: ${MEM_PERCENT}%"
    elif (( $(echo "$MEM_PERCENT > $MEM_WARN" | bc -l) )); then
        printf "${YELLOW}${MEM_USED}GB / ${MEM_TOTAL}GB (${MEM_PERCENT}%%)${NC} [WARNING]\n"
    else
        printf "${GREEN}${MEM_USED}GB / ${MEM_TOTAL}GB (${MEM_PERCENT}%%)${NC}\n"
    fi

    # Progress bar for Memory
    printf "["
    FILLED=$(awk "BEGIN {printf \"%.0f\", $MEM_PERCENT/2}")
    for ((i=0; i<50; i++)); do
        if [ $i -lt $FILLED ]; then printf "█"; else printf "░"; fi
    done
    printf "]\n\n"

    # GPU
    if [ "$GPU_AVAILABLE" = true ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "NVIDIA Tesla P40 GPU"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        printf "Utilization:  ${BLUE}${GPU_UTIL}%%${NC}\n"
        printf "VRAM:         ${BLUE}${GPU_MEM_USED}MB / ${GPU_MEM_TOTAL}MB (${GPU_MEM_PERCENT}%%)${NC}\n"

        printf "Temperature:  "
        if [ "$GPU_TEMP" -gt "$GPU_TEMP_CRIT" ]; then
            printf "${RED}${GPU_TEMP}°C${NC} [CRITICAL]\n"
            log_entry "ALERT: GPU temperature critical: ${GPU_TEMP}°C"
        elif [ "$GPU_TEMP" -gt "$GPU_TEMP_WARN" ]; then
            printf "${YELLOW}${GPU_TEMP}°C${NC} [WARNING]\n"
        else
            printf "${GREEN}${GPU_TEMP}°C${NC}\n"
        fi

        printf "Power:        ${BLUE}${GPU_POWER}${NC}\n"
        echo ""
    fi

    # Disk
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Storage (/mnt/user)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    printf "Usage: "
    if [ "$DISK_PERCENT" -gt "$DISK_WARN" ]; then
        printf "${RED}${DISK_USED}GB / ${DISK_TOTAL}GB (${DISK_PERCENT}%%)${NC} [WARNING]\n"
        log_entry "ALERT: Disk usage high: ${DISK_PERCENT}%"
    else
        printf "${GREEN}${DISK_USED}GB / ${DISK_TOTAL}GB (${DISK_PERCENT}%%)${NC}\n"
    fi
    echo ""

    # Network
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Network (bond0 - 4Gbps)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "Download: ${BLUE}${RX_RATE} MB/s${NC}  |  Upload: ${BLUE}${TX_RATE} MB/s${NC}\n"
    echo ""

    # Docker containers
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "OctoLLM Containers"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker ps --filter "name=octollm-" --format "table {{.Names}}\t{{.Status}}" | head -10
    echo ""

    echo "Press Ctrl+C to exit | Refreshing every 1 second | Log: $LOG_FILE"

done
