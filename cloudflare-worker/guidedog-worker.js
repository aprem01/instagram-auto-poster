/**
 * Guidedog - Cloudflare Worker API Proxy
 * Routes OpenAI API calls through Cloudflare for DVCCC Instagram Manager
 *
 * Deploy to: guidedog.kpremks.workers.dev
 *
 * Required Secrets (set in Cloudflare Dashboard):
 * - OPENAI_API_KEY: Your OpenAI API key
 * - ANTHROPIC_API_KEY: Your Anthropic API key (optional, for future use)
 */

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    const url = new URL(request.url);
    const path = url.pathname;

    // Health check endpoint
    if (path === '/health' || path === '/') {
      return new Response(JSON.stringify({
        status: 'ok',
        service: 'guidedog',
        timestamp: new Date().toISOString(),
        endpoints: {
          openai: '/v1/*',
          anthropic: '/anthropic/*'
        }
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // Route to appropriate API
    if (path.startsWith('/v1/')) {
      return handleOpenAI(request, env, path);
    } else if (path.startsWith('/anthropic/')) {
      return handleAnthropic(request, env, path);
    }

    return new Response(JSON.stringify({
      error: 'Not Found',
      message: 'Use /v1/* for OpenAI or /anthropic/* for Anthropic'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
};

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
};

function handleCORS() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders
  });
}

async function handleOpenAI(request, env, path) {
  const OPENAI_API_KEY = env.OPENAI_API_KEY;

  if (!OPENAI_API_KEY) {
    return new Response(JSON.stringify({
      error: 'Configuration Error',
      message: 'OPENAI_API_KEY not configured in worker secrets'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }

  const openaiUrl = `https://api.openai.com${path}`;

  // Clone request and modify headers
  const headers = new Headers(request.headers);
  headers.set('Authorization', `Bearer ${OPENAI_API_KEY}`);
  headers.delete('Host');

  try {
    const response = await fetch(openaiUrl, {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' ? request.body : undefined,
    });

    // Clone response and add CORS headers
    const responseHeaders = new Headers(response.headers);
    Object.entries(corsHeaders).forEach(([key, value]) => {
      responseHeaders.set(key, value);
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Proxy Error',
      message: error.message
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
}

async function handleAnthropic(request, env, path) {
  const ANTHROPIC_API_KEY = env.ANTHROPIC_API_KEY;

  if (!ANTHROPIC_API_KEY) {
    return new Response(JSON.stringify({
      error: 'Configuration Error',
      message: 'ANTHROPIC_API_KEY not configured in worker secrets'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }

  // Remove /anthropic prefix and forward to Anthropic API
  const anthropicPath = path.replace('/anthropic', '');
  const anthropicUrl = `https://api.anthropic.com${anthropicPath}`;

  const headers = new Headers(request.headers);
  headers.set('x-api-key', ANTHROPIC_API_KEY);
  headers.set('anthropic-version', '2023-06-01');
  headers.delete('Host');

  try {
    const response = await fetch(anthropicUrl, {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' ? request.body : undefined,
    });

    const responseHeaders = new Headers(response.headers);
    Object.entries(corsHeaders).forEach(([key, value]) => {
      responseHeaders.set(key, value);
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Proxy Error',
      message: error.message
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
}
