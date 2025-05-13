# Sentimark Newsletter Subscription System

This document describes the secure newsletter subscription system implemented for the Sentimark website, fully integrated with our existing Azure infrastructure.

## Architecture Overview

The newsletter subscription system integrates with our Azure Kubernetes Service (AKS) infrastructure and uses managed Azure services to ensure reliability, security, and scalability:

1. **Frontend Component**: JavaScript form handler with validation and submission logic
2. **Azure API Management**: Handles HTTP requests with authentication and rate limiting
3. **Azure Function (in AKS)**: Processes subscription requests securely
4. **Azure Cosmos DB**: Stores subscriber information within our existing data tier
5. **Azure Communication Services**: Sends confirmation emails
6. **Event Grid**: Notifies administrators of new subscriptions
7. **Azure Monitor**: Provides comprehensive system monitoring

![Newsletter System Architecture](../assets/images/newsletter-azure-architecture.png)

## Cost Analysis

This architecture is designed to be cost-effective while leveraging our existing Azure infrastructure:

| Component | Azure Service | Pricing | Estimated Monthly Cost |
|-----------|--------------|---------|------------------------|
| API | Azure API Management (Consumption) | ~$3.50 per million calls | $3.50 (for 1M calls) |
| Processing | Azure Functions (Consumption) | ~$0.20 per million executions | $0.20 (for 1M executions) |
| Storage | Azure Cosmos DB (Serverless) | ~$2.00 per million writes | $2.00 (for 1M writes) |
| Email | Azure Communication Services | ~$0.20 per 1,000 emails | $0.20 (for 1,000 emails) |
| Notifications | Event Grid | ~$0.60 per million operations | $0.60 (for 1M operations) |
| Monitoring | Azure Monitor | Included in existing infrastructure | $0.00 (included) |
| **Total** | | | **~$6.50** per month |

> **Note**: While the cost is slightly higher than an AWS solution, this approach offers better integration with our existing infrastructure, unified management, and leverages our team's Azure expertise.

The system can handle thousands of subscribers while remaining within the AWS free tier for most components, resulting in minimal operational costs.

## Security Features

The newsletter system includes multiple security measures, integrated with our existing Azure security framework:

1. **Azure AD Integration**: Uses our existing authentication framework
2. **Microsoft Defender for Cloud**: Provides comprehensive threat protection
3. **Rate Limiting**: Configurable policies via API Management
4. **Input Validation**: Prevents malformed data on client and server
5. **CORS Protection**: Restricts API access to the Sentimark domain
6. **IP Address Monitoring**: Fraud prevention with privacy protection
7. **Email Verification**: Confirms subscriber intent
8. **Azure Security Center**: Provides integrated security monitoring
9. **Web Application Firewall**: Protects against common attacks

## Privacy Considerations

The system is designed with privacy in mind:

1. Minimal data collection (email only by default)
2. IP addresses are hashed with a salt for fraud prevention
3. Admin notifications do not include full subscriber details
4. Confirmation emails include privacy policy
5. Unsubscribe link in all emails
6. GDPR-ready design with consent tracking (optional)

## Deployment Instructions

To deploy the newsletter system into our existing Azure infrastructure:

### 1. Deploy Azure Infrastructure using Terraform

```bash
# Navigate to the terraform directory
cd infrastructure/terraform/azure

# Initialize Terraform with the Azure backend
terraform init -backend-config=backends/prod.backend

# Apply the newsletter module
terraform apply -var-file=environments/prod.tfvars -target=module.newsletter
```

### 2. Deploy the Newsletter Service using Helm

```bash
# Navigate to the Helm directory
cd infrastructure/helm

# Update the Helm chart dependencies
helm dependency update sentimark-services

# Deploy or upgrade the service
helm upgrade --install sentimark-prod sentimark-services \
  -f values/prod.yaml \
  --set newsletter.enabled=true \
  --set newsletter.image.tag=latest \
  --namespace sentimark-prod
```

### 3. Set up Azure Communication Services

1. Configure the email sender domain in Azure Communication Services
2. Set up domain verification and SPF/DKIM records
3. Ensure the service is properly connected to our Azure Function

### 4. Update Website Configuration

1. Get the API endpoint and subscription key from Azure API Management
2. Update `_config.yml` with the API endpoint
3. Configure Microsoft Entra ID integration (optional)

### 5. Update the Form Include

Replace the current form with the new newsletter system:

```bash
# Backup existing form
cp _includes/newsletter-signup.html _includes/newsletter-signup.bak.html

# Use the new form
cp _includes/newsletter-signup-new.html _includes/newsletter-signup.html
```

## Monitoring and Maintenance

### Dashboard

Create an Azure Monitor dashboard to monitor:

- Subscription attempts
- Success rate
- Error rate
- Email delivery metrics
- API performance
- Resource utilization

### Regular Tasks

1. **Weekly**: Review subscription metrics via Azure Monitor
2. **Monthly**: Check for subscription growth trends and adjust resources if needed
3. **Quarterly**: Run a test subscription to verify system operation
4. **Biannually**: Review Azure security recommendations

## Alternative Options

While this custom Azure solution offers the best integration with our infrastructure, alternatives include:

1. **Mailchimp**: Better UI but higher cost ($17+/month after free tier)
2. **ConvertKit**: More features but higher cost ($9+/month)
3. **Sendinblue**: Good compromise option (free for up to 300 emails/day)
4. **Azure Serverless Solution**: Lower integration but potentially lower cost ($3-4/month)

The custom Azure AKS solution is recommended for its integration with our existing infrastructure, unified monitoring, and leveraging our team's expertise.

## Support and Troubleshooting

For issues with the newsletter system:

1. Check Azure Application Insights for function errors
2. Verify API Management configuration and policy settings
3. Test API endpoint with Postman
4. Check Azure Communication Services email logs
5. Verify Event Grid subscriptions are active
6. Review Azure Kubernetes Service logs for the newsletter service

For assistance, contact the development team at dev@sentimark.ai.