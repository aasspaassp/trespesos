import psutil
import time

# Azure IMDS
# Linux /proc/stat
# Linux proc/meminfo
# Azure monitor
# CPU Credits 
# CPU time
# Escuchar tráfico rx bytes, tx bytes
#time.process_time
# cgroupsv2 cpu.max cpu.stated
# Attested data nonce
# Azure carbon optimization

def collectCPUmetrics():
    cpuProc = psutil.cpu_times(percpu=False)
    print(cpuProc)
    networkIO1 = psutil.net_io_counters(pernic=False, nowrap=True)
    print(f"Network I/O: Sent={networkIO1.bytes_sent} bytes, Received={networkIO1.bytes_recv} bytes")
    cpuPercentage = psutil.cpu_percent(interval=1, percpu=False)
    print(f"CPU Percentage: {cpuPercentage}%")
    cpuStats = psutil.cpu_stats()
    print(cpuStats)
    cpuFreq = psutil.cpu_freq(percpu=False)
    print(f"CPU Frequency: {cpuFreq.current} MHz")
    disk = psutil.disk_usage('/')
    print(f"Disk Usage: {disk.percent}%")
    networkIO2 = psutil.net_io_counters(pernic=False, nowrap=True)
    print(f"Network I/O: Sent={networkIO2.bytes_sent} bytes, Received={networkIO2.bytes_recv} bytes")
    
    recieved_bytes = networkIO2.bytes_recv - networkIO1.bytes_recv
    sent_bytes = networkIO2.bytes_sent - networkIO1.bytes_sent


    meta = {
        "cpu_percentage": cpuPercentage,
        "cpu_frequencyMhz": cpuFreq.current,
        "disk_usage": disk.percent,
        "network_io": {
            "sent": sent_bytes,
            "received": recieved_bytes
        }
    }

    return meta



