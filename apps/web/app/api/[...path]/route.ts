const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://api:8000";

async function proxy(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const target = `${API_INTERNAL_URL}/api/${path.join("/")}${new URL(request.url).search}`;
  const response = await fetch(target, {
    method: request.method,
    headers: {
      "Content-Type": request.headers.get("Content-Type") ?? "application/json"
    },
    body: request.method === "GET" ? undefined : await request.text()
  });
  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/json"
    }
  });
}

export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export async function POST(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}
