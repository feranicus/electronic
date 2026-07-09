# Shodan Super Filters — Continental AG

_Seed: `AS211483` · generated 2026-07-06 · passive OSINT only._

## Identity
- ASNs: AS211483
- ASN holder: Continental AG
- Netblocks: 185.60.76.0/22, 192.109.198.0/24, 193.29.3.0/24, 2a04:5b40::/32
- Brand/Org: Continental AG
- Domains: continental.com

## Super filters

### 1. ASN sweep
_every host announced from the org's ASNs_
```
asn:AS211483
```

### 2. Netblock / CIDR (master)
_authoritative when the org has no own ASN / sits under a carrier_
```
net:185.60.76.0/22,192.109.198.0/24,193.29.3.0/24,2a04:5b40::/32
```

### 3. Org-name match
_reassigned/cloud/subsidiary ranges_
```
org:"Continental AG"
```

### 4. TLS cert subject CN
_shadow IT / cloud assets outside the block_
```
ssl.cert.subject.cn:"continental.com"
```

### 5. TLS free-text / cert org
_wildcard & SAN certs where CN != apex_
```
ssl:"Continental AG"
```

### 6. Hostname / domain
_reverse-DNS / HTTP host_
```
hostname:".continental.com"
```

### 7. Remote-access & DB ports
_3389 RDP·22 SSH·23 Telnet·5900 VNC·445 SMB·3306/1433/5432/6379/27017/9200 DB·21 FTP_
```
asn:AS211483 port:3389,22,23,5900,445,3306,1433,5432,6379,27017,9200,21
```

### 8. VPN / firewall mgmt
_edge-VPN appliances = #1 ransomware vector; facet by product_
```
asn:AS211483 port:443,4433,8443,10443,4443,500,4500,1194 product:"Citrix","Fortinet","Pulse Secure","Palo Alto","OpenVPN","SonicWall","Sophos","Cisco ASA"
```

### 9. RDP / WinRM / VNC
_3389/3390 RDP·5985/5986 WinRM·5900/5800 VNC_
```
asn:AS211483 port:3389,3390,5985,5986,5900,5800
```

### 10. OT / ICS / SCADA
_102 S7·502 Modbus·4840 OPC-UA·44818 EtherNet/IP·20000 DNP3·1911 Fox·47808 BACnet·789 Red Lion·2404 IEC-104_
```
asn:AS211483 tag:ics port:102,502,4840,44818,20000,1911,47808,789,9600,2404,20547 product:"Modbus","Siemens S7","BACnet","DNP3","IEC-104","OPC-UA"
```

### 11. Mail / Exchange / OWA
_on-prem SMTP/IMAP/POP + OWA login titles_
```
asn:AS211483 port:25,587,465,143,993,110,995
```

### 12. Vuln & TLS/EOL hygiene
_has_vuln/vuln require a Shodan paid plan (CISA KEV = CRITICAL)_
```
asn:AS211483 has_vuln:true  |  asn:AS211483 ssl.cert.expired:true  |  asn:AS211483 ssl.version:sslv3,tlsv1,tlsv1.1
```

### 13. Logins / panels / non-prod
_forgotten admin UIs, dev/staging_
```
asn:AS211483 http.title:"login","admin","portal","vpn","dashboard","phpMyAdmin","Webmin"
```

## Tips
- Shodan web UI ANDs space-separated terms and won't parse `OR` across net/asn/org — run each scope clause separately, then dedupe.
- `org:`/`isp:` are unreliable under carriers — trust `net:`, `ssl:`, `hostname:`.
- Add `country:XX` to localize; `-honeypot:true` to drop noise; save high-value clauses as Shodan Monitors.