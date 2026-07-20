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

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const backendBase = getBackendUrl(req.url);
    const id = (await params).id;
    const targetUrl = `${backendBase}/chat/session/${id}/messages`;
    
    const backendRes = await fetch(targetUrl, {
      method: 'GET',
      cache: 'no-store',
    });

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: 'Backend error', details: err.detail || `Status: ${backendRes.status}` },
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
