import { NextRequest, NextResponse } from 'next/server';

type RouteContext = { params: Promise<{ slug?: string[] }> };

export async function GET(req: NextRequest, { params }: RouteContext) {
  try {
    const backendBase = process.env.BACKEND_URL || 'http://localhost:8000';
    if (!/^https?:\/\//i.test(backendBase)) {
      throw new Error('BACKEND_URL must be an absolute HTTP(S) URL');
    }

    const { slug = [] } = await params;
    const url = `${backendBase.replace(/\/+$/, '')}/api/admin/${slug.join('/')}${req.nextUrl.search}`;
    const backendRes = await fetch(url, { cache: 'no-store' });
    const contentType = backendRes.headers.get('content-type');

    return new NextResponse(await backendRes.arrayBuffer(), {
      status: backendRes.status,
      headers: contentType ? { 'content-type': contentType } : undefined,
    });
  } catch (error: unknown) {
    const details = error instanceof Error ? error.message : 'Unknown proxy error';
    console.error('[Proxy GET /admin Error]', error);
    return NextResponse.json(
      { error: 'Backend connection error', details },
      { status: 502 },
    );
  }
}
