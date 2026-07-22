import { NextRequest, NextResponse } from 'next/server';
import { AI_MODELS, DEFAULT_MODEL } from '@/lib/constants';

function getBackendUrl(reqUrl: string): string {
  let base = process.env.BACKEND_URL || 'http://localhost:8000';
  if (base.startsWith('/')) {
    const { origin } = new URL(reqUrl);
    base = `${origin}${base}`;
  }
  return base.replace(/\/+$/, '');
}

function isSupportedModel(model: unknown): model is string {
  return typeof model === 'string' && AI_MODELS.some(item => item.id === model);
}

function normalizeChatBody(body: Record<string, unknown>) {
  const normalized = { ...body };
  const selectedModel = isSupportedModel(normalized.model) ? normalized.model : DEFAULT_MODEL;
  normalized.model = selectedModel;

  const inferenceConfig = normalized.inferenceConfig;
  if (inferenceConfig && typeof inferenceConfig === 'object' && !Array.isArray(inferenceConfig)) {
    const nextConfig = { ...(inferenceConfig as Record<string, unknown>) };
    const roles = nextConfig.roles;
    if (roles && typeof roles === 'object' && !Array.isArray(roles)) {
      const nextRoles: Record<string, unknown> = { ...(roles as Record<string, unknown>) };
      for (const role of ['answer', 'rewriter', 'summarizer']) {
        const setting = nextRoles[role];
        if (!setting || typeof setting !== 'object' || Array.isArray(setting)) continue;
        const nextSetting = { ...(setting as Record<string, unknown>) };
        if (!isSupportedModel(nextSetting.model)) {
          nextSetting.provider = 'google';
          nextSetting.model = DEFAULT_MODEL;
        }
        nextRoles[role] = nextSetting;
      }
      nextConfig.roles = nextRoles;
    }
    normalized.inferenceConfig = nextConfig;
  }

  return normalized;
}

export async function POST(req: NextRequest) {
  try {
    const rawBody = await req.json();
    const body = normalizeChatBody(rawBody);
    const backendBase = getBackendUrl(req.url);
    const streaming = body.streaming !== false;
    const targetUrl = `${backendBase}${streaming ? '/chat/stream' : '/chat'}`;

    const backendRes = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: req.signal,
    });

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: 'Backend error', details: err.detail || `Status: ${backendRes.status}` },
        { status: backendRes.status },
      );
    }

    if (!streaming) {
      return new NextResponse(await backendRes.arrayBuffer(), {
        status: backendRes.status,
        headers: { 'Content-Type': backendRes.headers.get('content-type') || 'application/json' },
      });
    }

    return new NextResponse(backendRes.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        Connection: 'keep-alive',
      },
    });
  } catch (error: unknown) {
    const details = error instanceof Error ? error.message : 'Unknown proxy error';
    console.error('[Proxy Chat Error]', error);
    return NextResponse.json(
      { error: 'Backend connection error', details },
      { status: 502 },
    );
  }
}
