const RAG_INTERNAL_URL = process.env.RAG_INTERNAL_URL ?? "http://rag-api:8090";

async function proxy(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const target = `${RAG_INTERNAL_URL}/${path.join("/")}`;
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
