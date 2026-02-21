import axios from "axios";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export interface AuthUser {
  id: number;
  email: string;
  display_name: string | null;
  is_admin: boolean;
  last_login_at: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface RegisterResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

function mapAuthError(err: unknown): never {
  if (axios.isAxiosError(err) && err.response) {
    const { status, data } = err.response;
    if (status === 401) {
      throw new Error("Invalid email or password");
    }
    if (status === 409) {
      throw new Error("An account with this email already exists");
    }
    if (status === 422) {
      const detail = data?.detail;
      if (Array.isArray(detail) && detail.length > 0) {
        const msg = detail[0]?.msg ?? "Validation error";
        throw new Error(String(msg));
      }
      if (typeof detail === "string") {
        throw new Error(detail);
      }
      throw new Error("Validation error");
    }
  }
  throw err instanceof Error ? err : new Error("An unexpected error occurred");
}

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  try {
    const { data } = await client.post<LoginResponse>("/api/auth/login", {
      email,
      password,
    });
    return data;
  } catch (err) {
    mapAuthError(err);
  }
}

export async function registerUser(
  email: string,
  password: string,
  displayName: string,
): Promise<RegisterResponse> {
  try {
    const { data } = await client.post<RegisterResponse>("/api/auth/register", {
      email,
      password,
      display_name: displayName,
    });
    return data;
  } catch (err) {
    mapAuthError(err);
  }
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  const { data } = await client.get<AuthUser>("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}
