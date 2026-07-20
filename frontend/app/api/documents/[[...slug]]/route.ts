import { NextRequest, NextResponse } from 'next/server';

type RouteContext = { params: Promise<{ slug?: string[] }> };

function getBackendUrl(): string {
  const base = process.env.BACKEND_URL || 'http://localhost:8000';

  if (!/^https?:\/\//i.test(base)) {
    throw new Error('BACKEND_URL must be an absolute HTTP(S) URL');
  }

  return base.replace(/\/+$/, '');
}

async function proxyRequest(req: NextRequest, { params }: RouteContext) {
  try {
    const backendBase = getBackendUrl();
    const resolvedParams = await params;
    const slugPath = resolvedParams.slug ? resolvedParams.slug.join('/') : '';
    const resourcePath = slugPath ? `/api/documents/${slugPath}` : '/api/documents/';
    const url = `${backendBase}${resourcePath}${req.nextUrl.search}`;
    const headers = new Headers();
    const contentType = req.headers.get('content-type');

    if (contentType) headers.set('content-type', contentType);

    const backendRes = await fetch(url, {
      method: req.method,
      headers,
      body: req.method === 'GET' || req.method === 'HEAD' ? undefined : await req.arrayBuffer(),
      cache: 'no-store',
      redirect: 'follow',
    });

    const responseHeaders = new Headers();
    const responseContentType = backendRes.headers.get('content-type');
    if (responseContentType) responseHeaders.set('content-type', responseContentType);

    return new NextResponse(await backendRes.arrayBuffer(), {
      status: backendRes.status,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const details = error instanceof Error ? error.message : 'Unknown proxy error';
    console.error(`[Proxy ${req.method} /documents Error]`, error);
    return NextResponse.json(
      { error: 'Backend connection error', details },
      { status: 502 },
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const DELETE = proxyRequest;
