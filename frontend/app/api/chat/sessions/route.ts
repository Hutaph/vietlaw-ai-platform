import { NextRequest, NextResponse } from 'next/server';

function getBackendUrl(reqUrl: string): string {
  let base = process.env.BACKEND_URL || 'http://localhost:8000';
  if (base.startsWith('/')) {
    const { origin } = new URL(reqUrl);
    base = `${origin}${base}`;
  }
  return base.replace(/\/+$/, '');
}

export const dynamic = 'force-dynamic';

async function readSafeErrorBody(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const payload = await response.json().catch(() => ({}));
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      return String(payload.detail).slice(0, 240);
    }
    if (payload && typeof payload === 'object' && 'error' in payload) {
      return String(payload.error).slice(0, 240);
    }
    return `Status: ${response.status}`;
  }
  const text = await response.text().catch(() => '');
  return text ? text.slice(0, 240) : `Status: ${response.status}`;
}

export async function GET(req: NextRequest) {
  try {
    const backendBase = getBackendUrl(req.url);
    const targetUrl = `${backendBase}/chat/sessions`;
    
    const backendRes = await fetch(targetUrl, {
      method: 'GET',
      cache: 'no-store',
    });

    if (!backendRes.ok) {
      const details = await readSafeErrorBody(backendRes);
      return NextResponse.json(
        { error: 'Backend error', details },
        { status: backendRes.status },
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const details = error instanceof Error ? error.message : 'Unknown proxy error';
    return NextResponse.json(
      { error: 'Backend connection error', details },
      { status: 502 },
    );
  }
}
