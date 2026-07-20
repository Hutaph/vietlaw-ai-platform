import { NextRequest, NextResponse } from 'next/server';

function getBackendUrl(reqUrl: string): string {
  let base = process.env.BACKEND_URL || 'http://localhost:8000';
  if (base.startsWith('/')) {
    const { origin } = new URL(reqUrl);
    base = `${origin}${base}`;
  }
  return base.replace(/\/+$/, '');
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const backendBase = getBackendUrl(req.url);
    const id = (await params).id;
    const targetUrl = `${backendBase}/chat/session/${id}`;
    console.log(`[Proxy Chat Delete] -> ${targetUrl}`);

    const backendRes = await fetch(targetUrl, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: 'Backend error', details: err.detail || `Status: ${backendRes.status}` },
        { status: backendRes.status },
      );
    }

    return NextResponse.json({ success: true });
  } catch (error: unknown) {
    const details = error instanceof Error ? error.message : 'Unknown proxy error';
    console.error('[Proxy Chat Delete Error]', error);
    return NextResponse.json(
      { error: 'Backend connection error', details },
      { status: 502 },
    );
  }
}
