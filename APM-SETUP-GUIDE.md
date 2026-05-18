# 🚀 APM Logging Setup & Troubleshooting Guide

**Project:** vn-address-intelligence  
**Date:** 2026-05-18  
**Status:** Connectivity Issue - Services Not Running

---

## 📊 Current Status

### Connectivity Test Results
```
✅ SSH (port 22):        OPEN - Server accessible
❌ Kibana (port 5601):   CLOSED - Service not running
❌ Elasticsearch (9200): CLOSED - Service not running
❌ APM Server (8200):    CLOSED - Service not running
```

### Configuration
```
APM Server Host: 138.2.68.67
APM Server Port: 8200
Elasticsearch: 138.2.68.67:9200
Kibana: 138.2.68.67:5601
App Name: vn-address-intelligence
```

---

## 🔧 Immediate Actions Required

### **Step 1: Access Server**

You need to SSH into the server to check/start services:

```bash
# Option A: With SSH key
ssh -i /path/to/private/key root@138.2.68.67

# Option B: With password
ssh root@138.2.68.67
```

### **Step 2: Check Service Status**

Once logged in, run:

```bash
# Check Elasticsearch
systemctl status elasticsearch
sudo systemctl start elasticsearch    # Start if stopped
sudo systemctl enable elasticsearch  # Enable on boot

# Check Kibana
systemctl status kibana
sudo systemctl start kibana
sudo systemctl enable kibana

# Check APM Server
systemctl status apm-server
sudo systemctl start apm-server
sudo systemctl enable apm-server
```

### **Step 3: Verify Services Running**

```bash
# Check if ports are listening
netstat -tlnp | grep -E '5601|9200|8200'

# Expected output:
# tcp  0  0 0.0.0.0:9200   0.0.0.0:*  LISTEN  xxxx/java
# tcp  0  0 0.0.0.0:5601   0.0.0.0:*  LISTEN  xxxx/node
# tcp  0  0 0.0.0.0:8200   0.0.0.0:*  LISTEN  xxxx/apm-server
```

### **Step 4: Check Firewall**

```bash
# Check firewall status
sudo ufw status

# If firewall is active, allow ports
sudo ufw allow 5601/tcp
sudo ufw allow 9200/tcp
sudo ufw allow 8200/tcp
sudo ufw reload
```

### **Step 5: Test from Local**

After services are running, test from your local machine:

```powershell
# PowerShell
Test-NetConnection -ComputerName 138.2.68.67 -Port 5601
Test-NetConnection -ComputerName 138.2.68.67 -Port 9200
Test-NetConnection -ComputerName 138.2.68.67 -Port 8200

# All should show: TcpTestSucceeded: True
```

---

## 📋 Service Startup Commands

### **Elasticsearch**

```bash
# Start
sudo systemctl start elasticsearch

# Check status
sudo systemctl status elasticsearch

# View logs
sudo tail -f /var/log/elasticsearch/elasticsearch.log

# Check if running
curl http://localhost:9200/
```

### **Kibana**

```bash
# Start
sudo systemctl start kibana

# Check status
sudo systemctl status kibana

# View logs
sudo tail -f /var/log/kibana/kibana.log

# Check if running
curl http://localhost:5601/
```

### **APM Server**

```bash
# Start
sudo systemctl start apm-server

# Check status
sudo systemctl status apm-server

# View logs
sudo tail -f /var/log/apm-server/apm-server.log

# Check if running
curl http://localhost:8200/
```

---

## 🔍 Troubleshooting

### **If Elasticsearch won't start**

```bash
# Check logs
sudo tail -f /var/log/elasticsearch/elasticsearch.log

# Common issues:
# 1. Not enough memory - increase heap size
# 2. Port already in use - check with: netstat -tlnp | grep 9200
# 3. Disk space full - check with: df -h

# Restart
sudo systemctl restart elasticsearch
```

### **If Kibana won't start**

```bash
# Check logs
sudo tail -f /var/log/kibana/kibana.log

# Common issues:
# 1. Elasticsearch not running - start Elasticsearch first
# 2. Port 5601 already in use
# 3. Configuration error

# Restart
sudo systemctl restart kibana
```

### **If APM Server won't start**

```bash
# Check logs
sudo tail -f /var/log/apm-server/apm-server.log

# Common issues:
# 1. Elasticsearch not running
# 2. Port 8200 already in use
# 3. Configuration error

# Restart
sudo systemctl restart apm-server
```

---

## 🎯 After Services Are Running

### **1. Create Data View in Kibana**

1. Open Kibana: http://138.2.68.67:5601
2. Go to **Stack Management** → **Data Views**
3. Click **Create data view**
4. Configure:
   - **Name:** `vn-address-intelligence-logs`
   - **Index pattern:** `logs-apm.app-default`
   - **Timestamp field:** `@timestamp`
5. Click **Save**

### **2. View Logs in Discover**

1. Go to **Discover**
2. Select data view: `vn-address-intelligence-logs`
3. Logs should appear

### **3. Verify Application Logs**

1. Make API requests to your app
2. Check Kibana Discover for new logs
3. Verify log structure and fields

---

## 📊 Expected Log Format

When logs appear in Kibana, they should look like:

```json
{
  "@timestamp": "2026-05-18T07:22:56.947Z",
  "log.level": "INFO",
  "log.logger": "VNAI",
  "message": "HTTP GET /api/parser - 200 (45ms)",
  "service.name": "vn-address-intelligence",
  "service.environment": "production",
  "log.origin.file.name": "server.py",
  "log.origin.file.line": 690,
  "log.origin.function": "logging_middleware"
}
```

---

## ✅ Verification Checklist

- [ ] SSH into server 138.2.68.67
- [ ] Elasticsearch running: `systemctl status elasticsearch`
- [ ] Kibana running: `systemctl status kibana`
- [ ] APM Server running: `systemctl status apm-server`
- [ ] Ports open: `netstat -tlnp | grep -E '5601|9200|8200'`
- [ ] Firewall allows ports: `ufw allow 5601/tcp` etc.
- [ ] Test from local: `Test-NetConnection -ComputerName 138.2.68.67 -Port 5601`
- [ ] Data View created in Kibana
- [ ] Logs visible in Discover
- [ ] Application sending logs successfully

---

## 🚨 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Port 5601 closed | Kibana not running | `sudo systemctl start kibana` |
| Port 9200 closed | Elasticsearch not running | `sudo systemctl start elasticsearch` |
| Port 8200 closed | APM Server not running | `sudo systemctl start apm-server` |
| "No data streams" | No indices created | Wait for logs to be sent |
| Logs not appearing | App not sending logs | Check `KIBANA_LOG_ENABLED=true` |
| Connection timeout | Firewall blocking | `sudo ufw allow 5601/tcp` |

---

## 📞 Support

**If you need help:**

1. Check service logs: `sudo tail -f /var/log/elasticsearch/elasticsearch.log`
2. Check firewall: `sudo ufw status`
3. Check ports: `netstat -tlnp | grep -E '5601|9200|8200'`
4. Restart services: `sudo systemctl restart elasticsearch kibana apm-server`

---

## 🎯 Next Steps

1. **SSH into server** - Get access to 138.2.68.67
2. **Start services** - Elasticsearch, Kibana, APM Server
3. **Open firewall** - Allow ports 5601, 9200, 8200
4. **Test connectivity** - Verify ports from local
5. **Create Data View** - In Kibana
6. **View logs** - In Discover

---

**Status: READY FOR DEPLOYMENT** 🚀

Once services are running and firewall is configured, the APM logging system will be fully operational.
