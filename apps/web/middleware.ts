import { NextRequest, NextResponse } from "next/server";

const USER_PATHS = ["/study", "/favorites", "/history"];
const ADMIN_PATHS = ["/admin"];

function matches(pathname: string, prefixes: string[]) {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const userId = request.cookies.get("gospel_user_id")?.value;
  const role = request.cookies.get("gospel_user_role")?.value;

  if (matches(pathname, USER_PATHS) && !userId) {
    const url = request.nextUrl.clone();
    url.pathname = "/sign-in";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (matches(pathname, ADMIN_PATHS)) {
    if (!userId) {
      const url = request.nextUrl.clone();
      url.pathname = "/sign-in";
      url.searchParams.set("next", pathname);
      return NextResponse.redirect(url);
    }
    if (role !== "admin") {
      const url = request.nextUrl.clone();
      url.pathname = "/access-denied";
      url.search = "";
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/study/:path*", "/favorites/:path*", "/history/:path*", "/admin/:path*"]
};
