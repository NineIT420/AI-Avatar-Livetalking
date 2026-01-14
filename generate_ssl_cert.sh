#!/bin/bash
# Generate self-signed SSL certificate for HTTPS testing
# For production, use certificates from a trusted CA (e.g., Let's Encrypt)

echo "Generating self-signed SSL certificate..."
echo "Note: Browsers will show a security warning for self-signed certificates."
echo "For production use, obtain certificates from Let's Encrypt or another trusted CA."
echo ""

# Create certs directory if it doesn't exist
mkdir -p certs

# Generate private key
openssl genrsa -out certs/server.key 2048

# Generate certificate signing request and self-signed certificate
openssl req -new -x509 -key certs/server.key -out certs/server.crt -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

echo ""
echo "Certificate generated successfully!"
echo "Files created:"
echo "  - certs/server.crt (certificate)"
echo "  - certs/server.key (private key)"
echo ""
echo "To use with the server, run:"
echo "  python app.py --ssl_cert certs/server.crt --ssl_key certs/server.key --transport webrtc --model musetalk --avatar_id avatar1"
echo ""
echo "For production, replace these with certificates from a trusted CA."

