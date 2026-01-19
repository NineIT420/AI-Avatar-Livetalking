const { createServer } = require('https');
const { parse } = require('url');
const next = require('next');
const fs = require('fs');
const path = require('path');

const dev = process.env.NODE_ENV !== 'production';
const hostname = process.env.HOSTNAME || '0.0.0.0';
const port = process.env.PORT || 3000;

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

// Paths for SSL certificates
const certPath = path.join(__dirname, 'cert.pem');
const keyPath = path.join(__dirname, 'key.pem');

// Function to generate self-signed certificate
function generateSelfSignedCert() {
  const { execSync } = require('child_process');
  console.log('Generating self-signed SSL certificate...');
  try {
    execSync(
      `openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"`,
      { stdio: 'inherit', cwd: __dirname }
    );
    console.log('SSL certificate generated successfully!');
  } catch (error) {
    console.error('Failed to generate SSL certificate:', error.message);
    console.error('Please install OpenSSL or provide your own certificates (cert.pem and key.pem)');
    process.exit(1);
  }
}

// Check if certificates exist, if not generate them
if (!fs.existsSync(certPath) || !fs.existsSync(keyPath)) {
  generateSelfSignedCert();
}

// Read SSL certificates
let httpsOptions;
try {
  httpsOptions = {
    key: fs.readFileSync(keyPath),
    cert: fs.readFileSync(certPath),
  };
} catch (error) {
  console.error('Error reading SSL certificates:', error.message);
  process.exit(1);
}

app.prepare().then(() => {
  createServer(httpsOptions, async (req, res) => {
    try {
      const parsedUrl = parse(req.url, true);
      await handle(req, res, parsedUrl);
    } catch (err) {
      console.error('Error occurred handling', req.url, err);
      res.statusCode = 500;
      res.end('internal server error');
    }
  }).listen(port, hostname, (err) => {
    if (err) throw err;
    console.log(`> Ready on https://${hostname === '0.0.0.0' ? 'localhost' : hostname}:${port}`);
    console.log('> Using HTTPS with self-signed certificate');
    console.log('> Note: Your browser may show a security warning for self-signed certificates');
  });
});

