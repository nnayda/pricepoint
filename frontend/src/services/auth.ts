import axios from "axios";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
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

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>("/api/auth/login", {
    email,
    password,
  });
  return data;
}

export async function registerUser(
  email: string,
  password: string,
  displayName: string,
): Promise<RegisterResponse> {
  const { data } = await client.post<RegisterResponse>("/api/auth/register", {
    email,
    password,
    display_name: displayName,
  });
  return data;
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  const { data } = await client.get<AuthUser>("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}
