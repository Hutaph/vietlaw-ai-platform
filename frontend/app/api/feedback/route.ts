import { NextResponse } from 'next/server';
import { FeedbackPayload } from '@/lib/types';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: Request) {
  try {
    const payload: FeedbackPayload = await req.json();

    const response = await fetch(`${BACKEND_URL}/api/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Feedback API error:', errorText);
      // We don't want to break the UI just because feedback failed,
      // so we still return a 200 with an error status.
      return NextResponse.json({ status: 'error', message: 'Failed to save feedback on backend' }, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error proxying feedback request:', error);
    return NextResponse.json(
      { status: 'error', message: 'Internal server error while processing feedback' },
      { status: 200 } // Keep it 200 so UI doesn't crash on feedback submission
    );
  }
}
