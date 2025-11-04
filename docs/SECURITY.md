# Security Best Practices

## Overview

This document outlines security best practices for the AppliedAI Email Classifier POC, focusing on client secret management, OAuth security, data protection, and compliance requirements.

---

## Client Secret Management

### Current Setup (POC)

**Storage Location**: `.env` file (local development)
**Description**: `poc-local-dev`
**Expiration**: 24 months from creation
**Rotation Policy**: Manual, before expiration

### ⚠️ Critical Security Rules

#### 1. NEVER Commit Secrets to Git

- `.env` is in `.gitignore` - verify before committing
- Use git pre-commit hooks if needed
- Check commits before pushing: `git diff --cached`
- If accidentally committed: immediately rotate secret and force-push removal

```bash
# Check if .env is gitignored
git check-ignore .env  # Should output: .env

# Verify .env not in staging
git status  # Should NOT show .env
```

#### 2. Copy Secret Value Immediately

- Azure only shows client secret value **once**
- You cannot retrieve it later
- Store securely immediately:
  - Password manager (recommended)
  - `.env` file (local development only)
- Never store in:
  - Email
  - Slack/Teams messages
  - Cloud storage (Dropbox, Google Drive, etc.)
  - Screenshots or text files in shared locations

**When Creating Secret:**
```
1. Azure Portal → App Registration → Certificates & secrets
2. New client secret
3. Description: "poc-local-dev"
4. Expires: 24 months
5. Click "Add"
6. ⚠️ IMMEDIATELY copy the "Value" field (NOT the "Secret ID")
7. Paste into .env file or password manager
8. Verify you copied the correct value (test authentication)
```

#### 3. Rotate Before Expiration

- **Set calendar reminder** for 23 months from creation date
- Rotation process:
  1. Create new secret: `poc-local-dev-2`
  2. Update `.env` with new secret
  3. Test authentication thoroughly
  4. Delete old secret only after confirming new one works
  5. Update calendar reminder for new secret

**Rotation Checklist:**
- [ ] Create new client secret in Azure Portal
- [ ] Update `CLIENT_SECRET` in `.env`
- [ ] Restart application
- [ ] Test authentication flow
- [ ] Test email fetching and classification
- [ ] Delete old secret from Azure Portal
- [ ] Set calendar reminder for new secret expiration

#### 4. Protect Your `.env` File

- **Never share** via email, Slack, Teams, or any messaging platform
- **Never upload** to cloud storage or file sharing services
- **Keep file permissions restrictive:**

```bash
# Set .env to read/write for owner only
chmod 600 .env

# Verify permissions
ls -l .env  # Should show: -rw-------
```

- **Never copy** `.env` to shared directories
- **Always use** `.env.example` as template for team members
- **Each developer** should create their own `.env` with their own credentials

---

## Production Migration (Phase 8)

### Azure Key Vault Integration

**Why Key Vault?**
- ✅ No secrets in application code or config files
- ✅ Automatic rotation with Azure Functions
- ✅ Audit logging (who accessed what, when)
- ✅ RBAC access control
- ✅ Automatic versioning of secrets
- ✅ Integration with App Service managed identity

#### Setup Steps (Future)

```bash
# 1. Create Key Vault
az keyvault create \
  --name kv-appliedai-classifier \
  --resource-group rg-appliedai-classifier-poc \
  --location eastus

# 2. Add secrets
az keyvault secret set \
  --vault-name kv-appliedai-classifier \
  --name "client-secret" \
  --value "your-secret-value"

az keyvault secret set \
  --vault-name kv-appliedai-classifier \
  --name "azure-openai-key" \
  --value "your-openai-key"

# 3. Grant App Service access (managed identity)
az keyvault set-policy \
  --name kv-appliedai-classifier \
  --object-id <app-service-managed-identity-id> \
  --secret-permissions get list
```

#### Code Implementation (Future)

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Use managed identity (no secrets in code!)
credential = DefaultAzureCredential()
client = SecretClient(
    vault_url="https://kv-appliedai-classifier.vault.azure.com/",
    credential=credential
)

# Retrieve secrets at runtime
client_secret = client.get_secret("client-secret").value
openai_key = client.get_secret("azure-openai-key").value

# Secrets are never stored in code or config files
```

#### Automatic Rotation with Azure Functions

```python
# Azure Function triggered monthly
def rotate_client_secret(timer):
    # 1. Create new client secret
    new_secret = create_app_registration_secret(
        app_registration_id=APP_REG_ID,
        description=f"prod-{datetime.now().strftime('%Y%m')}"
    )

    # 2. Update Key Vault
    kv_client.set_secret("client-secret", new_secret.value)

    # 3. Wait 24 hours for propagation
    time.sleep(86400)

    # 4. Delete old secret
    delete_old_app_registration_secret(old_secret_id)

    # 5. Send notification
    send_notification("Client secret rotated successfully")
```

---

## OAuth Security

### POC Safeguards

#### Implemented Security Measures

1. **State Parameter** - Prevents CSRF attacks
   ```python
   state = secrets.token_urlsafe(32)  # 256-bit random token
   auth_state_store[state] = time.time()
   # Validated in callback
   ```

2. **Single Tenant** - University of Iowa directory only
   - Supported account types: "Accounts in this organizational directory only"
   - No personal Microsoft accounts (outlook.com, hotmail.com)
   - No multi-tenant applications

3. **Server-Side Token Storage** - Not in cookies or localStorage
   ```python
   # Tokens stored in server memory, never sent to client
   user_tokens["demo_user"] = {
       "access_token": token,
       "expires_at": expiry
   }
   ```

4. **HTTPS Required** - In production deployment
   - Enforced by Azure App Service
   - TLS 1.2 minimum
   - HSTS headers enabled

#### Current Limitations (POC)

- ⚠️ No token encryption at rest (acceptable for POC)
- ⚠️ No automatic token refresh (must re-authenticate)
- ⚠️ In-memory storage (data lost on restart)
- ⚠️ Single-user only (demo_user)
- ⚠️ No rate limiting
- ⚠️ No audit logging

### Production Requirements (IT-15 Compliance)

#### IT-15 Policy Requirements

The University of Iowa IT-15 policy mandates:

1. **Multi-Factor Authentication (MFA)**
   - Enable Conditional Access policies in Azure AD
   - Require MFA for all users accessing the application
   - Support hardware tokens (YubiKey) for high-risk scenarios

2. **Session Timeout**
   - 20 minutes for public-facing applications
   - 60 minutes for internal applications
   - Automatic logout on timeout

3. **Audit Logging**
   - Log all authentication events
   - Log all data access events
   - Retain logs for 12 months minimum
   - Enable Azure AD sign-in logs
   - Enable Application Insights telemetry

4. **Network Restrictions**
   - IP whitelisting for sensitive operations
   - VPN requirement for off-campus access
   - Azure Private Link for database connections

5. **Conditional Access**
   - Block access from risky sign-ins
   - Require compliant devices
   - Enforce device enrollment

#### Implementation Checklist (Phase 8)

- [ ] Enable MFA in Azure AD Conditional Access
- [ ] Configure session timeout (20 minutes)
- [ ] Enable Azure AD sign-in audit logs
- [ ] Enable Application Insights
- [ ] Configure IP restrictions for App Service
- [ ] Implement device compliance checks
- [ ] Set up Azure Sentinel for security monitoring
- [ ] Complete security review with University IT
- [ ] Obtain IT-15 compliance certification

---

## Data Protection

### Email Data Handling

#### POC (Test Data Only)

**Current State:**
- Using `appliedai.demo@outlook.com` (no real student data)
- In-memory processing only (no persistent storage)
- Data cleared on server restart
- No encryption at rest (acceptable for test data)
- No data retention policy needed

#### Production (Real Student Data)

**FERPA Compliance Requirements:**

The Family Educational Rights and Privacy Act (FERPA) requires:

1. **Minimize Data Collection**
   - Only collect data necessary for classification
   - Don't store email bodies long-term
   - Store only: subject, category, timestamp, confidence
   - Purge processed emails after 30 days

2. **Encrypt Data at Rest**
   ```sql
   -- Azure SQL Database with Transparent Data Encryption (TDE)
   -- Automatically enabled for all Azure SQL databases
   ```

3. **Encrypt Data in Transit**
   - TLS 1.2+ for all connections
   - Certificate pinning for API calls
   - HTTPS-only redirect

4. **Access Control**
   - Role-Based Access Control (RBAC)
   - Principle of least privilege
   - Audit all data access

5. **Data Retention**
   - Processed emails: 30 days
   - Classification results: 90 days
   - Audit logs: 12 months
   - Automated purging with Azure Functions

#### Implementation Example (Phase 8)

```python
from azure.sql import Database
from cryptography.fernet import Fernet

class SecureEmailStorage:
    def __init__(self):
        self.db = Database(connection_from_keyvault())
        self.encryption_key = get_encryption_key_from_keyvault()
        self.cipher = Fernet(self.encryption_key)

    def store_classification(self, email):
        # Store minimal data only
        record = {
            "internet_message_id": email.id,
            "subject": self.cipher.encrypt(email.subject),  # Encrypted
            "category": email.category,
            "confidence": email.confidence,
            "processed_at": datetime.utcnow(),
            "retention_until": datetime.utcnow() + timedelta(days=30)
        }
        self.db.insert("processed_emails", record)

    def purge_old_data(self):
        # Automatic purging triggered daily
        self.db.delete(
            "processed_emails",
            where="retention_until < GETUTCDATE()"
        )
```

---

## Incident Response

### If Client Secret Compromised

**Immediate Actions (Within 1 Hour):**

1. **Revoke compromised secret** in Azure Portal
   - Azure AD → App registrations → `app-appliedai-classifier-poc`
   - Certificates & secrets → Delete compromised secret
   - This immediately invalidates all tokens

2. **Generate new secret** with updated description
   - Description: `poc-local-dev-emergency-YYYYMMDD`
   - Expires: 3 months (shorter than normal during incident)
   - Copy value immediately

3. **Update application** with new secret
   - Update `.env` file
   - Restart application
   - Test authentication

4. **Audit access logs** in Azure AD
   - Check sign-in logs for unauthorized access
   - Review API calls for unusual patterns
   - Check for data exfiltration attempts

5. **Report to IT Security** if institutional data exposed
   - Email: security@uiowa.edu
   - Include: timeline, scope, actions taken
   - Follow University incident response procedures

**Follow-Up Actions (Within 24 Hours):**

- [ ] Review how compromise occurred
- [ ] Implement additional safeguards
- [ ] Update documentation with lessons learned
- [ ] Schedule security training if needed
- [ ] Rotate all other secrets as precaution

### If Access Token Leaked

**Immediate Actions:**

1. **Revoke user sessions** in Azure Portal
   - Azure AD → Users → Select user → Sign-ins
   - Revoke sessions (invalidates all refresh tokens)

2. **Change user password** if needed
   - If personal account: user changes password
   - If organization account: IT admin resets password

3. **Review audit logs** for unauthorized access
   - Check Graph API calls
   - Look for unusual email access patterns
   - Check for category modifications

4. **Enable Conditional Access** to prevent future issues
   - Require MFA
   - Restrict to trusted devices
   - Add IP restrictions

**Recovery:**

- User re-authenticates with new credentials
- Monitor for 48 hours for unusual activity
- No data breach if action taken within 1 hour

### If Data Breach Occurs

**Immediate Actions (Within 1 Hour):**

1. **Contain the breach**
   - Revoke all access immediately
   - Shut down affected services
   - Preserve logs for investigation

2. **Assess scope**
   - How many records affected?
   - What type of data exposed?
   - FERPA-protected data involved?

3. **Notify stakeholders**
   - IT Security: security@uiowa.edu
   - University Counsel if FERPA data
   - Affected users within 72 hours (GDPR/FERPA requirement)

4. **Preserve evidence**
   - Copy all logs before they rotate
   - Screenshot configuration
   - Document timeline

**Follow-Up:**

- [ ] Complete incident report
- [ ] Implement corrective measures
- [ ] Notify affected individuals
- [ ] Update security practices
- [ ] Re-certify IT-15 compliance

---

## Compliance Checklist

### Before Production Deployment

#### IT-15 Compliance

- [ ] Multi-factor authentication enabled
- [ ] Conditional Access policies configured
- [ ] Session timeout implemented (20 minutes)
- [ ] Audit logging enabled (Azure AD + Application Insights)
- [ ] Network restrictions in place (IP whitelisting)
- [ ] Device compliance enforced
- [ ] Security review completed with University IT
- [ ] Penetration testing performed

#### FERPA Compliance

- [ ] Data minimization implemented
- [ ] Encryption at rest enabled (Azure SQL TDE)
- [ ] Encryption in transit enforced (TLS 1.2+)
- [ ] Access controls implemented (RBAC)
- [ ] Data retention policy configured (30 days)
- [ ] Automated data purging implemented
- [ ] Privacy impact assessment completed
- [ ] User consent forms prepared

#### Azure Security

- [ ] All secrets in Azure Key Vault
- [ ] Managed identity configured
- [ ] Private endpoints for databases
- [ ] Network Security Groups configured
- [ ] Azure Security Center enabled
- [ ] Azure Defender enabled
- [ ] Diagnostic logging enabled
- [ ] Backup and disaster recovery tested

#### Code Security

- [ ] Dependency scanning (Dependabot)
- [ ] Static code analysis (SonarQube)
- [ ] Secret scanning (git-secrets)
- [ ] Container scanning (if using containers)
- [ ] Code review required for all changes
- [ ] Branch protection rules enforced

---

## Security Monitoring

### Azure Monitor Alerts (Phase 8)

Configure alerts for:

1. **Authentication Anomalies**
   - Failed login attempts > 5 in 10 minutes
   - New login location
   - Login from risky IP address
   - MFA failure

2. **Data Access Anomalies**
   - Unusual email access volume (>100/hour)
   - Access outside business hours
   - Access from new device/location
   - Multiple users accessed by single token

3. **Application Errors**
   - 401/403 errors spike
   - 500 errors > 1% of requests
   - API rate limiting exceeded
   - Database connection failures

4. **Cost Anomalies**
   - Daily cost > $50 (may indicate attack)
   - Token usage spike (>10K tokens/hour)
   - API call volume spike

### Response Procedures

**High Priority (Respond within 1 hour):**
- Authentication failures
- Data breach indicators
- Service outages

**Medium Priority (Respond within 4 hours):**
- Cost anomalies
- Performance degradation
- Non-critical errors

**Low Priority (Respond within 24 hours):**
- Configuration warnings
- Deprecation notices
- Maintenance reminders

---

## Resources

### University of Iowa Policies

- [IT-15: Access Control Policy](https://itsecurity.uiowa.edu/policies/it-15)
- [FERPA Compliance Guide](https://registrar.uiowa.edu/ferpa)
- [Data Classification Guidelines](https://itsecurity.uiowa.edu/data-classification)

### Microsoft Documentation

- [Azure Security Best Practices](https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns)
- [Azure Key Vault Best Practices](https://learn.microsoft.com/azure/key-vault/general/best-practices)
- [Conditional Access Deployment Guide](https://learn.microsoft.com/azure/active-directory/conditional-access/plan-conditional-access)

### Training

- [Azure Security Training](https://learn.microsoft.com/training/paths/secure-your-cloud-data/)
- [FERPA Training](https://registrar.uiowa.edu/ferpa/training)
- [University IT Security Training](https://itsecurity.uiowa.edu/training)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-04 | Initial security documentation for POC |

---

## Contact

For security concerns or incidents:

- **University IT Security**: security@uiowa.edu
- **University IT Helpdesk**: (319) 384-4357
- **Emergency**: Call IT Security immediately if data breach suspected
