import { AuthConfigResponse, User } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function getAuthConfig(): Promise<AuthConfigResponse> {
  const response = await fetch(`${API_URL}/api/auth/config`);
  if (!response.ok) {
    throw new Error("Failed to fetch auth config");
  }
  return response.json();
}

export async function getUser(): Promise<User | null> {
  const response = await fetch(`${API_URL}/api/auth/user`);
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export const fetchUser = async (): Promise<User | null> => {
  try {
    const response = await fetch(`${API_URL}/api/auth/user`);
    if (response.ok) {
      const data = await response.json();
      return data.user;
    }
  } catch (error) {
    console.error("Error fetching user:", error);
  }
  return null;
};

export const handleLogin = (authConfig: AuthConfigResponse | null) => {
  if (authConfig?.google_login_url) {
    window.location.href = authConfig.google_login_url;
  }
};

export const handleLogout = (authConfig: AuthConfigResponse | null) => {
  if (authConfig?.logout_url) {
    window.location.href = authConfig.logout_url;
  }
};
