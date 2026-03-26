import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { BackgroundOrbs } from '../components/ui/BackgroundOrbs';

export function GoogleCalendarCallbackPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const success = params.get('success');
    const error = params.get('error');

    sessionStorage.removeItem('oauth_state');

    if (success === 'true') {
      setStatus('success');
      setMessage('Google Calendar connected successfully!');
      setTimeout(() => navigate('/settings'), 2000);
    } else if (error) {
      setStatus('error');
      setMessage(
        error === 'access_denied'
          ? 'Calendar connection was cancelled.'
          : `OAuth error: ${error}`
      );
    } else {
      setStatus('error');
      setMessage('Unexpected callback — missing success or error parameter.');
    }
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <BackgroundOrbs />

      <div className="relative z-10 max-w-md w-full">
        <div className="glass rounded-2xl p-12 text-center">
          {status === 'loading' && (
            <>
              <Loader className="w-12 h-12 mx-auto mb-6 text-cyan-400 animate-spin" />
              <h2 className="text-2xl font-display font-semibold text-white mb-2">
                Connecting Google Calendar...
              </h2>
              <p className="text-gray-400">
                Please wait while we complete the setup.
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="w-12 h-12 mx-auto mb-6 text-emerald-400" />
              <h2 className="text-2xl font-display font-semibold text-white mb-2">
                Success!
              </h2>
              <p className="text-gray-400 mb-6">{message}</p>
              <p className="text-sm text-gray-500">Redirecting to settings...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <AlertCircle className="w-12 h-12 mx-auto mb-6 text-red-400" />
              <h2 className="text-2xl font-display font-semibold text-white mb-2">
                Connection Failed
              </h2>
              <p className="text-gray-400 mb-6">{message}</p>
              <button
                onClick={() => navigate('/settings')}
                className="px-6 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-xl text-white font-semibold transition-all"
              >
                Back to Settings
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
