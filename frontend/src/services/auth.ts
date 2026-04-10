/**
 * Auth service — handles JWT storage and authentication API calls.
 *
 * Tokens are persisted in localStorage under the key "token".  All API
 * requests automatically attach the stored token via the axios interceptor
 * configured in api.ts.
 */

import { api } from './api';

const TOKEN_KEY = 'token';

// ---------------------------------------------------------------------------
// Token storage helpers
// ---------------------------------------------------------------------------

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

/**
 * Authenticate with the API and store the returned JWT.
 *
 * @param username - Account username or email address.
 * @param password - Plain-text password.
 * @returns The raw token response from the server.
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { username, password });
  setToken(data.access_token);
  return data;
}

/**
 * Register a new user account.
 *
 * @param email - Valid email address.
 * @param username - Desired username (3–100 characters).
 * @param password - Password (minimum 8 characters).
 */
export async function register(email: string, username: string, password: string): Promise<UserProfile> {
  const { data } = await api.post<UserProfile>('/auth/register', { email, username, password });
  return data;
}

/**
 * Fetch the authenticated user's profile from the server.
 *
 * Requires a valid JWT to be stored (i.e. the user must be logged in).
 */
export async function fetchMe(): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>('/auth/me');
  return data;
}

/**
 * Remove the stored token, effectively logging the user out.
 */
export function logout(): void {
  clearToken();
}
