import { ApiError, ErrorEnvelope } from '../types';

export class ClienteApiError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ClienteApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export class ClienteHttp {
  private baseUrl: string;
  private token: string | null = null;
  private onUnauthorizedCallback: (() => void) | null = null;

  constructor(baseUrl?: string) {
    const envUrl = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL;
    this.baseUrl = baseUrl ?? envUrl ?? '/api/v1';
    if (typeof localStorage !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
  }

  setToken(token: string | null): void {
    this.token = token;
    if (typeof localStorage !== 'undefined') {
      if (token) {
        localStorage.setItem('token', token);
      } else {
        localStorage.removeItem('token');
      }
    }
  }

  getToken(): string | null {
    if (!this.token && typeof localStorage !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  setOnUnauthorized(callback: () => void): void {
    this.onUnauthorizedCallback = callback;
  }

  private handleUnauthorized(): void {
    this.setToken(null);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('usuario');
    }
    if (this.onUnauthorizedCallback) {
      this.onUnauthorizedCallback();
    }
  }

  async peticion<T>(ruta: string, init: RequestInit = {}): Promise<T> {
    const url = ruta.startsWith('http')
      ? ruta
      : `${this.baseUrl}${ruta.startsWith('/') ? '' : '/'}${ruta}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const respuesta = await fetch(url, {
      ...init,
      headers,
    });

    if (respuesta.status === 401) {
      this.handleUnauthorized();
    }

    if (!respuesta.ok) {
      let code = 'ERROR_DESCONOCIDO';
      let message = `Error de API HTTP ${respuesta.status}`;
      let details: unknown = undefined;

      try {
        const cuerpo = (await respuesta.json()) as ErrorEnvelope | ApiError;
        if ('error' in cuerpo && cuerpo.error) {
          code = cuerpo.error.code || code;
          message = cuerpo.error.message || message;
          details = cuerpo.error.details;
        } else if ('code' in cuerpo && 'message' in cuerpo) {
          code = cuerpo.code;
          message = cuerpo.message;
          details = cuerpo.details;
        }
      } catch {
        message = respuesta.statusText || message;
      }

      throw new ClienteApiError(code, message, respuesta.status, details);
    }

    if (respuesta.status === 204) {
      return undefined as unknown as T;
    }

    return (await respuesta.json()) as T;
  }

  get<T>(ruta: string, options?: RequestInit): Promise<T> {
    return this.peticion<T>(ruta, { ...options, method: 'GET' });
  }

  post<T>(ruta: string, body?: unknown, options?: RequestInit): Promise<T> {
    return this.peticion<T>(ruta, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  put<T>(ruta: string, body?: unknown, options?: RequestInit): Promise<T> {
    return this.peticion<T>(ruta, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(ruta: string, body?: unknown, options?: RequestInit): Promise<T> {
    return this.peticion<T>(ruta, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(ruta: string, options?: RequestInit): Promise<T> {
    return this.peticion<T>(ruta, { ...options, method: 'DELETE' });
  }
}

export const clienteApi = new ClienteHttp();
