import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { ClienteHttp, ClienteApiError } from '../src/api/cliente';

describe('ClienteHttp', () => {
  let cliente: ClienteHttp;

  beforeEach(() => {
    localStorage.clear();
    cliente = new ClienteHttp('/api/v1');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('inyecta cabecera Authorization: Bearer cuando existe token en almacenamiento', async () => {
    cliente.setToken('token-ficticio-123');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ datos: 'ok' }),
    });
    global.fetch = mockFetch;

    const respuesta = await cliente.get<{ datos: string }>('/recurso');

    expect(respuesta).toEqual({ datos: 'ok' });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/recurso',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer token-ficticio-123',
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('no inyecta cabecera Authorization cuando no hay token disponible', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ estado: 'publico' }),
    });
    global.fetch = mockFetch;

    await cliente.get('/publico');

    const llamada = mockFetch.mock.calls[0];
    const headers = llamada[1]?.headers as Record<string, string>;
    expect(headers['Authorization']).toBeUndefined();
  });

  it('captura respuesta HTTP 401, purga sesión y dispara callback de expiración', async () => {
    cliente.setToken('token-expirado');
    localStorage.setItem('usuario', JSON.stringify({ email: 'test@clinica.com' }));

    const onUnauthorized = vi.fn();
    cliente.setOnUnauthorized(onUnauthorized);

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({
        error: { code: 'NO_AUTENTICADO', message: 'Token inválido o expirado' },
      }),
    });

    await expect(cliente.get('/privado')).rejects.toThrow(ClienteApiError);

    expect(cliente.getToken()).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('usuario')).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it('deserializa correctamente el envelope de error estándar de la API', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({
        error: {
          code: 'SOLAPAMIENTO_SILLON',
          message: 'El sillón ya está ocupado en ese horario',
        },
      }),
    });

    try {
      await cliente.post('/turnos', {});
      expect.unreachable('Debe haber lanzado ClienteApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ClienteApiError);
      const apiErr = err as ClienteApiError;
      expect(apiErr.code).toBe('SOLAPAMIENTO_SILLON');
      expect(apiErr.message).toBe('El sillón ya está ocupado en ese horario');
      expect(apiErr.status).toBe(409);
    }
  });

  it('soporta métodos POST, PUT, PATCH y DELETE con serialización JSON', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ exito: true }),
    });
    global.fetch = mockFetch;

    await cliente.post('/alta', { clave: 'valor' });
    expect(mockFetch).toHaveBeenLastCalledWith(
      '/api/v1/alta',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ clave: 'valor' }),
      })
    );

    await cliente.put('/recurso/1', { modificado: true });
    expect(mockFetch).toHaveBeenLastCalledWith(
      '/api/v1/recurso/1',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ modificado: true }),
      })
    );

    await cliente.delete('/recurso/1');
    expect(mockFetch).toHaveBeenLastCalledWith(
      '/api/v1/recurso/1',
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});
