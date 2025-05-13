/**
 * AWS Lambda Function for Newsletter Subscription
 * 
 * This Lambda function handles newsletter subscription requests from the Sentimark website.
 * It validates input, performs security checks, and stores subscriber data in DynamoDB.
 * It can optionally integrate with a third-party service like Mailchimp or SendGrid.
 */

const AWS = require('aws-sdk');
const https = require('https');
const crypto = require('crypto');

// Initialize AWS clients
const dynamoDB = new AWS.DynamoDB.DocumentClient();
const sns = new AWS.SNS();
const ses = new AWS.SES({ region: 'us-east-1' });

// Environment variables (set in Lambda configuration)
const TABLE_NAME = process.env.SUBSCRIBERS_TABLE_NAME || 'sentimark-subscribers';
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || 'admin@sentimark.ai';
const RECAPTCHA_SECRET = process.env.RECAPTCHA_SECRET;
const API_KEYS = (process.env.ALLOWED_API_KEYS || 'sm_newsletter_webapp').split(',');
const NOTIFICATION_TOPIC = process.env.NOTIFICATION_TOPIC;

// Email configuration - use a verified SES identity
const SENDER_EMAIL = process.env.SENDER_EMAIL || 'newsletter@sentimark.ai';
const CONFIRMATION_TEMPLATE = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to Sentimark's Newsletter</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <img src="https://sentimark.ai/assets/images/logos/sentimark-logo.svg" alt="Sentimark Logo" width="200">
        </div>
        
        <h1 style="color: #2E5BFF;">Thank You for Subscribing!</h1>
        
        <p>Dear Subscriber,</p>
        
        <p>Thank you for joining the Sentimark newsletter! We're excited to keep you updated on our progress, including our upcoming Kickstarter campaign and product developments.</p>
        
        <p>You'll receive periodic updates with insights into our innovative sentiment analysis platform, market trends, and exclusive early access opportunities.</p>
        
        <div style="background-color: #f5f7ff; padding: 15px; border-radius: 5px; margin: 25px 0;">
            <p style="margin: 0; font-weight: bold;">Stay Connected:</p>
            <p style="margin: 10px 0 0;">
                <a href="https://sentimark.ai/product/" style="color: #2E5BFF; text-decoration: none;">Learn about our product</a> | 
                <a href="https://sentimark.ai/kickstarter/" style="color: #2E5BFF; text-decoration: none;">Kickstarter campaign</a>
            </p>
        </div>
        
        <p>We respect your privacy and promise not to share your email address. You can unsubscribe at any time by clicking the unsubscribe link in our emails.</p>
        
        <p>Best regards,<br>The Sentimark Team</p>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #777; text-align: center;">
            <p>Sentimark AI | Uncovering hidden alpha through sentiment analysis</p>
            <p>
                <a href="https://sentimark.ai/privacy-policy/" style="color: #2E5BFF; text-decoration: none;">Privacy Policy</a> | 
                <a href="https://sentimark.ai/contact/" style="color: #2E5BFF; text-decoration: none;">Contact Us</a>
            </p>
        </div>
    </div>
</body>
</html>
`;

/**
 * Lambda handler function
 */
exports.handler = async (event) => {
    // Set up CORS headers for API Gateway integration
    const headers = {
        'Access-Control-Allow-Origin': 'https://sentimark.ai',
        'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key',
        'Access-Control-Allow-Methods': 'OPTIONS,POST'
    };
    
    // Handle preflight OPTIONS request
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({ message: 'CORS preflight request successful' })
        };
    }
    
    try {
        // Validate request method
        if (event.httpMethod !== 'POST') {
            return errorResponse(405, 'Method not allowed', headers);
        }
        
        // Parse request body
        const body = JSON.parse(event.body || '{}');
        
        // Basic API key verification
        const apiKey = event.headers['X-Api-Key'] || event.headers['x-api-key'];
        if (!apiKey || !API_KEYS.includes(apiKey)) {
            return errorResponse(403, 'Invalid API key', headers);
        }
        
        // Validate required fields
        if (!body.email) {
            return errorResponse(400, 'Email is required', headers);
        }
        
        // Validate email format
        if (!isValidEmail(body.email)) {
            return errorResponse(400, 'Invalid email format', headers);
        }
        
        // Optional - Verify reCAPTCHA token if provided
        if (RECAPTCHA_SECRET && body.recaptchaToken) {
            const recaptchaValid = await verifyRecaptcha(body.recaptchaToken);
            if (!recaptchaValid) {
                return errorResponse(400, 'reCAPTCHA verification failed', headers);
            }
        }
        
        // Check for duplicate email
        const existingSubscriber = await checkExistingSubscriber(body.email);
        if (existingSubscriber) {
            // Don't reveal if email exists for privacy/security reasons
            return successResponse({ 
                message: 'Thank you for your interest in our newsletter!'
            }, headers);
        }
        
        // Create unique subscriber ID and confirmation token
        const subscriberId = crypto.randomUUID();
        const confirmationToken = crypto.randomBytes(32).toString('hex');
        const timestamp = new Date().toISOString();
        
        // Store subscriber in DynamoDB
        await storeSubscriber({
            id: subscriberId,
            email: body.email.toLowerCase(),
            confirmationToken,
            source: body.source || 'website',
            ipHash: hashIP(event.requestContext?.identity?.sourceIp || ''),
            createdAt: timestamp,
            confirmed: false,
            status: 'pending'
        });
        
        // Send confirmation email
        await sendConfirmationEmail(body.email);
        
        // Optional - Notify admin about new subscriber via SNS
        if (NOTIFICATION_TOPIC) {
            await notifyAdmin(body.email, body.source);
        }
        
        // Return success response
        return successResponse({ 
            success: true,
            message: 'Subscription successful! Please check your email to confirm.'
        }, headers);
        
    } catch (error) {
        console.error('Error processing subscription:', error);
        return errorResponse(500, 'An error occurred processing your request', headers);
    }
};

/**
 * Helper functions
 */

// Validate email format
function isValidEmail(email) {
    const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return regex.test(email);
}

// Check if email already exists in the database
async function checkExistingSubscriber(email) {
    const params = {
        TableName: TABLE_NAME,
        IndexName: 'EmailIndex',
        KeyConditionExpression: 'email = :email',
        ExpressionAttributeValues: {
            ':email': email.toLowerCase()
        }
    };
    
    const result = await dynamoDB.query(params).promise();
    return result.Items && result.Items.length > 0;
}

// Store subscriber in DynamoDB
async function storeSubscriber(subscriber) {
    const params = {
        TableName: TABLE_NAME,
        Item: subscriber
    };
    
    return dynamoDB.put(params).promise();
}

// Send confirmation email using Amazon SES
async function sendConfirmationEmail(email) {
    const params = {
        Source: SENDER_EMAIL,
        Destination: {
            ToAddresses: [email]
        },
        Message: {
            Subject: {
                Data: 'Welcome to Sentimark Newsletter!'
            },
            Body: {
                Html: {
                    Data: CONFIRMATION_TEMPLATE
                }
            }
        }
    };
    
    return ses.sendEmail(params).promise();
}

// Notify admin about new subscriber
async function notifyAdmin(email, source) {
    const message = `New newsletter subscriber: ${email} (from: ${source || 'website'})`;
    
    const params = {
        TopicArn: NOTIFICATION_TOPIC,
        Message: message,
        Subject: 'New Sentimark Newsletter Subscriber'
    };
    
    return sns.publish(params).promise();
}

// Verify reCAPTCHA token
async function verifyRecaptcha(token) {
    return new Promise((resolve) => {
        const data = new URLSearchParams();
        data.append('secret', RECAPTCHA_SECRET);
        data.append('response', token);
        
        const options = {
            hostname: 'www.google.com',
            port: 443,
            path: '/recaptcha/api/siteverify',
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        };
        
        const req = https.request(options, (res) => {
            let responseData = '';
            
            res.on('data', (chunk) => {
                responseData += chunk;
            });
            
            res.on('end', () => {
                try {
                    const parsedResponse = JSON.parse(responseData);
                    resolve(parsedResponse.success === true);
                } catch (e) {
                    console.error('Error parsing reCAPTCHA response:', e);
                    resolve(false);
                }
            });
        });
        
        req.on('error', (e) => {
            console.error('Error verifying reCAPTCHA:', e);
            resolve(false);
        });
        
        req.write(data.toString());
        req.end();
    });
}

// Hash IP address for privacy
function hashIP(ip) {
    if (!ip) return '';
    return crypto
        .createHash('sha256')
        .update(ip + process.env.IP_SALT || 'sentimark-salt')
        .digest('hex');
}

// Format error response
function errorResponse(statusCode, message, headers) {
    return {
        statusCode,
        headers,
        body: JSON.stringify({
            success: false,
            message
        })
    };
}

// Format success response
function successResponse(data, headers) {
    return {
        statusCode: 200,
        headers,
        body: JSON.stringify(data)
    };
}