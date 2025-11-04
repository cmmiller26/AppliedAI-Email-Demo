# Azure AI Foundry Setup Guide

## Overview

This project uses **Azure AI Foundry** (formerly Azure AI Studio) as the unified platform for AI operations. Azure AI Foundry provides a centralized hub for managing Azure OpenAI deployments along with additional features like monitoring, evaluation, and Prompt Flow.

## Why Azure AI Foundry?

Microsoft recommends Azure AI Foundry for building production AI applications because it provides:

1. **Better Project Organization**: Hub → Project → Resources hierarchy
2. **Built-in Monitoring**: Track usage, performance, and costs in real-time
3. **Evaluation Tools**: Test model accuracy with datasets
4. **Prompt Flow**: Visual designer for complex AI workflows
5. **Model Catalog**: Easy access to multiple AI models
6. **Content Safety**: Built-in filtering and moderation
7. **Cost Visibility**: Project-level spending insights

---

## Current Setup

### Resources Created
- **Hub**: `aih-appliedai-classifier-poc` (North Central US)
- **Project**: `aip-appliedai-classifier-poc`
- **Deployment**: `gpt-4o-mini`

### Architecture

```
┌─────────────────────────────────────────┐
│      Azure AI Foundry Hub               │
│  (aih-appliedai-classifier-poc)         │
│           Region: North Central US      │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │   Azure AI Foundry Project        │  │
│  │  (aip-appliedai-classifier-poc)   │  │
│  │                                   │  │
│  │  Connected Resources:             │  │
│  │  • Azure OpenAI Service           │  │
│  │  • Monitoring & Evaluation        │  │
│  │  • Prompt Flow (optional)         │  │
│  └───────────────────────────────────┘  │
└──────────┬──────────────────────────────┘
           │
           ▼
    ┌─────────────────┐
    │   FastAPI App   │
    │   (Your Code)   │
    └─────────────────┘
```

---

## Code Compatibility

✅ **No code changes needed!** The existing `openai` Python SDK works seamlessly with AI Foundry.

### Before AI Foundry (Direct Azure OpenAI)
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
```

### After AI Foundry (No Changes!)
```python
from openai import AzureOpenAI

# Same code - just point to AI Foundry's OpenAI endpoint
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  # Now from AI Foundry
)
```

The endpoint format is identical - AI Foundry exposes the same Azure OpenAI API.

---

## Setup Steps (For Reference)

### 1. Create AI Foundry Hub

```bash
# Azure Portal → AI Foundry → Create New Hub
Resource Group: rg-appliedai-classifier-poc
Hub Name: aih-appliedai-classifier-poc
Region: North Central US
Network: All networks (POC), Selected networks (Production)
```

### 2. Create AI Foundry Project

```bash
# Within the Hub → Projects → Create New Project
Project Name: aip-appliedai-classifier-poc
Hub: aih-appliedai-classifier-poc
Description: Email classification POC using GPT-4o-mini
```

### 4. Deploy Model

```bash
# Project → Deployments → Deploy Model
Model: gpt-4o-mini
Deployment Name: gpt-4o-mini
Tokens per Minute: 10K (adjustable)
Content Filter: Default (adjustable)
```

### 5. Get Credentials

```bash
# Project → Settings → Properties
1. Copy "Endpoint" (Azure OpenAI endpoint URL)
2. Go to Keys and Endpoint → Copy Key 1
3. Update .env file with both values
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Azure OpenAI Service (connected to AI Foundry)
AZURE_OPENAI_KEY=your_key_from_ai_foundry
AZURE_OPENAI_ENDPOINT=https://aih-appliedai-classifier-poc.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Optional: AI Foundry Connection String

For advanced features like Prompt Flow, you can use the AI Foundry connection string:

```bash
# Optional (for native AI Foundry SDK features)
AZURE_AI_PROJECT_CONNECTION_STRING=your_connection_string_here
```

Get this from: **AI Foundry Portal → Your Project → Settings → Connection String**

---

## Benefits Over Direct Azure OpenAI

| Feature | Direct Azure OpenAI | Azure AI Foundry |
|---------|-------------------|------------------|
| **Model Deployment** | ✅ Manual | ✅ Guided UI |
| **Token Usage Tracking** | Basic (Azure billing) | ✅ Real-time dashboards |
| **Evaluation Datasets** | ❌ Manual setup | ✅ Built-in tools |
| **Prompt Flow** | ❌ None | ✅ Visual designer |
| **Content Safety** | ❌ Manual configuration | ✅ Pre-configured filters |
| **Multi-model Management** | ❌ Separate resources | ✅ Unified catalog |
| **Cost Tracking** | Azure billing only | ✅ Project-level insights |
| **A/B Testing** | ❌ Manual | ✅ Built-in experiments |
| **Monitoring Alerts** | ❌ Manual setup | ✅ One-click alerts |
| **Team Collaboration** | ❌ Limited | ✅ Role-based access |

### Pricing

**Good News:** Azure AI Foundry has **no additional cost** beyond Azure OpenAI pricing!

- gpt-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens
- Same pricing as direct Azure OpenAI Service
- No platform fees or premiums

---

## Current Usage (POC Phase)

### What We Use Now
- ✅ Model deployment (gpt-4o-mini)
- ✅ Basic monitoring (token usage, latency)
- ✅ OpenAI SDK integration (seamless compatibility)

### What We Don't Use Yet (Future Enhancements)
- ⏳ Evaluation datasets (Phase 7-8)
- ⏳ Prompt Flow (Phase 7-8)
- ⏳ Content safety filters (Phase 8)
- ⏳ A/B testing experiments (Phase 8)
- ⏳ Advanced monitoring alerts (Phase 8)

---

## Future Features (Phase 7-8)

### 1. Prompt Flow Integration

**What is Prompt Flow?**
Visual designer for building, testing, and deploying complex LLM workflows without code.

**Use Case for Email Classification:**
```
[Fetch Email] → [Sanitize Content] → [Classify with GPT-4o-mini]
    → [Confidence Check] → [Assign Outlook Category]
           ↓ (if confidence < 0.7)
    [Fallback to Rule-Based Classification]
```

**Benefits:**
- Visual debugging of classification pipeline
- Easy A/B testing of different prompts
- Non-developers can modify workflows
- Built-in version control

**Setup:**
```bash
# AI Foundry Portal → Your Project → Prompt Flow → Create New Flow
1. Import classification flow template
2. Configure nodes (input, LLM, output)
3. Test with sample emails
4. Deploy as REST endpoint
```

---

### 2. Evaluation Datasets

**What are Evaluation Datasets?**
Test sets with labeled examples to measure classification accuracy over time.

**Use Case:**
```python
# Upload test_emails.csv with labeled categories
email_id,subject,from,body,expected_category
1,"CS 4980 Assignment","prof@uiowa.edu","Due Friday...","ACADEMIC"
2,"Club Meeting Tonight","club@uiowa.edu","Join us...","SOCIAL"
...
```

**How to Use:**
1. Create test dataset in AI Foundry
2. Run batch evaluation
3. View accuracy metrics
4. Compare prompt variations
5. Track accuracy over time

**Metrics Tracked:**
- Overall accuracy (% correct)
- Per-category precision/recall
- Confidence score distribution
- Latency per classification
- Cost per 1000 emails

---

### 3. A/B Testing Experiments

**What is A/B Testing in AI Foundry?**
Compare different models, prompts, or parameters to optimize performance.

**Example Experiment:**
```
Variant A: GPT-4o-mini with current prompt (baseline)
Variant B: GPT-4o-mini with simplified prompt (test cost reduction)
Variant C: GPT-4o with current prompt (test accuracy improvement)

Metrics: Accuracy, Latency, Cost per 1000 emails
```

**Setup:**
```bash
# AI Foundry Portal → Your Project → Experiments → Create Experiment
1. Define variants (different prompts/models)
2. Upload test dataset
3. Run experiment
4. Compare results in dashboard
5. Select winning variant
```

---

### 4. Content Safety Filters

**What are Content Safety Filters?**
Built-in filters to detect:
- Profanity and inappropriate language
- Harassment and bullying
- PII (personally identifiable information)
- Sexual content
- Violence

**Use Case for Email Classification:**
- Flag emails with inappropriate content
- Redact PII before classification
- Block unsafe content from being processed
- Compliance with data protection regulations

**Setup:**
```bash
# AI Foundry Portal → Your Project → Content Safety → Configure Filters
1. Enable content safety
2. Set severity thresholds (low, medium, high)
3. Configure actions (block, flag, redact)
4. Test with sample emails
```

---

### 5. Advanced Monitoring & Alerts

**Monitoring Dashboards:**
- Real-time token usage
- Classification latency (avg, p50, p95, p99)
- Error rate and types
- Cost trends (daily, weekly, monthly)
- Model performance metrics

**Alerts:**
```bash
# AI Foundry Portal → Your Project → Monitoring → Create Alert
Examples:
- Alert if latency > 3 seconds (95th percentile)
- Alert if error rate > 5%
- Alert if daily cost > $50
- Alert if accuracy drops below 80%
```

**Notification Options:**
- Email
- SMS
- Azure Logic Apps
- Webhook (integrate with Slack, Teams, etc.)

---

## Migration Notes

### What Changed
✅ Using Azure AI Foundry as management platform
✅ Azure OpenAI connected through AI Foundry project
✅ Enhanced monitoring and evaluation capabilities
✅ Better resource organization

### What Stayed the Same
✅ Python code using `openai` SDK (no changes)
✅ API endpoints and authentication
✅ Model deployments (gpt-4o-mini)
✅ Application functionality
✅ Environment variable names
✅ Pricing (same as direct Azure OpenAI)

---

## Accessing AI Foundry Portal

### Portal URL
https://ai.azure.com/

### Navigation
```
1. Sign in with Azure account
2. Select your hub: aih-appliedai-classifier-poc
3. Select your project: aip-appliedai-classifier-poc
4. Explore features:
   - Dashboard (overview)
   - Deployments (manage models)
   - Prompt Flow (visual designer)
   - Evaluation (test datasets)
   - Monitoring (usage metrics)
   - Settings (credentials, connections)
```

---

## Troubleshooting

### Issue: "No OpenAI endpoint found"
**Solution:**
1. Verify project has connected Azure OpenAI resource
2. Check Settings → Connections → Azure OpenAI Service
3. Ensure deployment name matches `AZURE_OPENAI_DEPLOYMENT` in `.env`

### Issue: "Authentication failed"
**Solution:**
1. Regenerate API key in AI Foundry Portal
2. Update `AZURE_OPENAI_KEY` in `.env`
3. Restart FastAPI server

### Issue: "Model not found"
**Solution:**
1. Check Project → Deployments
2. Verify `gpt-4o-mini` is deployed
3. Ensure deployment name matches `.env` configuration

### Issue: "Rate limit exceeded"
**Solution:**
1. Check Project → Deployments → gpt-4o-mini → Settings
2. Increase Tokens Per Minute (TPM) quota
3. Or implement rate limiting in application code

---

## Resources & Documentation

### Official Microsoft Documentation
- [Azure AI Foundry Overview](https://learn.microsoft.com/azure/ai-studio/)
- [Azure OpenAI in AI Foundry](https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-openai)
- [Prompt Flow Guide](https://learn.microsoft.com/azure/ai-studio/how-to/prompt-flow)
- [Evaluation in AI Foundry](https://learn.microsoft.com/azure/ai-studio/how-to/evaluate-generative-ai-app)
- [Content Safety](https://learn.microsoft.com/azure/ai-studio/concepts/content-filtering)

### Tutorials
- [Build your first AI app with AI Foundry](https://learn.microsoft.com/azure/ai-studio/tutorials/deploy-chat-web-app)
- [Evaluate GPT model performance](https://learn.microsoft.com/azure/ai-studio/how-to/evaluate-prompts-playground)
- [Create Prompt Flow for classification](https://learn.microsoft.com/azure/ai-studio/how-to/flow-develop)

### Community
- [Azure AI Community Discord](https://discord.gg/azure-ai)
- [GitHub - Azure AI Samples](https://github.com/Azure-Samples/azure-ai-studio-samples)
- [Stack Overflow - azure-ai-studio tag](https://stackoverflow.com/questions/tagged/azure-ai-studio)

---

## Best Practices

### Security
- ✅ Store API keys in Azure Key Vault (production)
- ✅ Use managed identities instead of connection strings
- ✅ Enable private endpoints for production workloads
- ✅ Rotate API keys regularly (every 90 days)
- ✅ Use role-based access control (RBAC) for team members

### Cost Optimization
- ✅ Use gpt-4o-mini for cost-effective classification
- ✅ Monitor token usage in AI Foundry dashboards
- ✅ Set budget alerts in Azure Cost Management
- ✅ Cache classification results to avoid re-processing
- ✅ Use Batch API for large overnight jobs (50% discount)

### Performance
- ✅ Implement parallel processing (Phase 7)
- ✅ Set appropriate TPM quotas based on load
- ✅ Monitor latency and set alerts for degradation
- ✅ Use evaluation datasets to track accuracy over time
- ✅ Test prompt variations with A/B experiments

### Reliability
- ✅ Implement retry logic with exponential backoff
- ✅ Set up monitoring alerts for errors and latency
- ✅ Use fallback classification if AI Foundry unavailable
- ✅ Test disaster recovery procedures
- ✅ Document runbooks for common issues

---

## Conclusion

Azure AI Foundry provides a robust, production-ready platform for AI applications with:
- ✅ Zero code changes required for migration
- ✅ Enhanced monitoring and evaluation tools
- ✅ No additional cost beyond Azure OpenAI pricing
- ✅ Foundation for advanced features (Prompt Flow, evaluation, etc.)
- ✅ Better alignment with Microsoft's recommended practices

This migration sets the foundation for future enhancements in Phases 7-8!
