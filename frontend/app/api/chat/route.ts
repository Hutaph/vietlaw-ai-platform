import { NextRequest, NextResponse } from 'next/server';

function getBackendUrl(reqUrl: string): string {
  let base = process.env.BACKEND_URL || 'http://localhost:8000';
  if (base.startsWith('/')) {
    const { origin } = new URL(reqUrl);
    base = `${origin}${base}`;
  }
  return base.replace(/\/+$/, '');
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
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
