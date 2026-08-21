const API_BASE_URL =
  import.meta.env.VITE_API_URL || "https://maverick-hackathon.onrender.com";

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("tm_token");

  const url = path.startsWith("http")
    ? path
    : `${API_BASE_URL}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {}),
        ...(options.headers || {}),
      },
    });
  } catch (err: any) {
    console.error("Network error fetching URL:", url, err);
    throw new Error(`Unable to connect to backend service (${url}). Please check backend server status.`);
  }

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem("tm_token");
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }

    let errorMsg = `HTTP ${res.status}`;

    try {
      const data = await res.json();

      if (typeof data === "string") {
        errorMsg = data;
      } else if (data?.detail) {
        errorMsg =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      } else if (data?.message) {
        errorMsg = data.message;
      } else {
        errorMsg = JSON.stringify(data);
      }
    } catch {
      const text = await res.text();
      errorMsg = text || errorMsg;
    }

    throw new Error(errorMsg);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}