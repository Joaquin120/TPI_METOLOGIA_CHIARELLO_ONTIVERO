import React, { useState, FormEvent, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { iniciarSesion, estaAutenticado } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const destino = (location.state as { from?: { pathname: string } })?.from?.pathname || '/agenda';

  useEffect(() => {
    if (estaAutenticado) {
      navigate('/agenda', { replace: true });
    }
  }, [estaAutenticado, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError('Por favor complete todos los campos');
      return;
    }

    setSubmitting(true);
    try {
      await iniciarSesion({ email: email.trim(), password });
      navigate(destino, { replace: true });
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error ? err.message : 'Credenciales inválidas o error de conexión';
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-container" data-testid="login-container">
      <div className="login-card">
        <div className="login-header">
          <span className="login-logo">🦷</span>
          <h1>Sistema de Turnos</h1>
          <p>Ingrese sus credenciales para acceder a la plataforma</p>
        </div>

        {error && (
          <div className="alert alert-error" data-testid="login-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Correo Electrónico</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ejemplo@clinica.com"
              required
              autoFocus
              data-testid="input-email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              data-testid="input-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={submitting}
            data-testid="btn-login"
          >
            {submitting ? 'Ingresando...' : 'Iniciar Sesión'}
          </button>
        </form>

        <div className="login-footer">
          <small className="texto-muted">
            Consultorio Odontológico • Plataforma SaaS de Gestión Clínica
          </small>
        </div>
      </div>
    </div>
  );
};
