import { useState } from 'react';
import {
  Mail,
  Calendar,
  CheckCircle,
  AlertCircle,
  Loader,
} from 'lucide-react';
import { api } from '../lib/api';

interface CalendarProvider {
  name: string;
  icon: React.ReactNode;
  connected: boolean;
  email?: string;
  lastSync?: string;
}

export function SettingsPage() {
  const [providers, setProviders] = useState<CalendarProvider[]>([
    {
      name: 'Google Calendar',
      icon: <Mail className="w-5 h-5" />,
      connected: false,
    },
    {
      name: 'Calendly',
      icon: <Calendar className="w-5 h-5" />,
      connected: false,
    },
  ]);
  const [connecting, setConnecting] = useState<string | null>(null);

  const handleConnect = async (name: string) => {
    setConnecting(name);
    try {
      let data: { authorization_url: string };
      if (name === 'Google Calendar') {
        data = await api.startGoogleCalendarOAuth();
      } else {
        data = await api.startCalendlyOAuth();
      }
      // Store state for validation on callback
      const url = new URL(data.authorization_url);
      const state = url.searchParams.get('state');
      if (state) {
        sessionStorage.setItem('oauth_state', state);
      }
      window.location.href = data.authorization_url;
    } catch (err) {
      console.error('OAuth initiation error:', err);
      setConnecting(null);
    }
  };

  const handleDisconnect = async (name: string) => {
    try {
      if (name === 'Google Calendar') {
        await api.disconnectGoogleCalendar();
      } else {
        await api.disconnectCalendly();
      }
      setProviders((prev) =>
        prev.map((p) =>
          p.name === name
            ? { ...p, connected: false, email: undefined, lastSync: undefined }
            : p
        )
      );
    } catch (err) {
      console.error('Disconnect error:', err);
    }
  };

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-display font-semibold tracking-[-0.02em] text-white mb-1">
          Settings
        </h1>
        <p className="text-gray-400 text-sm font-medium">
          Manage your calendar integrations and preferences
        </p>
      </div>

      {/* Calendar Integrations */}
      <div className="glass rounded-2xl p-6 sm:p-8 mb-8">
        <h2 className="text-2xl font-display font-semibold tracking-tight text-white mb-2">
          Calendar Integrations
        </h2>
        <p className="text-gray-400 text-sm mb-8">
          Connect your calendars to automatically sync bookings and check availability in
          real-time.
        </p>

        <div className="space-y-4">
          {providers.map((provider) => (
            <div
              key={provider.name}
              className="border border-white/10 rounded-xl p-4 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:border-white/20 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white/5 rounded-lg text-white">
                  {provider.icon}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">
                    {provider.name}
                  </h3>
                  {provider.connected ? (
                    <div className="flex items-center gap-2 text-sm text-emerald-400 mt-1">
                      <CheckCircle className="w-4 h-4" />
                      Connected as {provider.email}
                      {provider.lastSync && (
                        <span className="text-gray-500">
                          &middot; Last sync {provider.lastSync}
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-sm mt-1">Not connected</p>
                  )}
                </div>
              </div>

              <button
                onClick={() =>
                  provider.connected
                    ? handleDisconnect(provider.name)
                    : handleConnect(provider.name)
                }
                disabled={connecting === provider.name}
                className={`px-6 py-2 rounded-xl font-semibold transition-all whitespace-nowrap disabled:opacity-50 ${
                  provider.connected
                    ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30'
                    : 'bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border border-cyan-500/30'
                }`}
              >
                {connecting === provider.name ? (
                  <span className="flex items-center gap-2">
                    <Loader className="w-4 h-4 animate-spin" />
                    Connecting...
                  </span>
                ) : provider.connected ? (
                  'Disconnect'
                ) : (
                  'Connect'
                )}
              </button>
            </div>
          ))}
        </div>

        <div className="mt-6 flex gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-200">
            <strong>Why connect?</strong> Automatically create events when bookings
            are confirmed, check availability in real-time, and prevent double
            bookings.
          </div>
        </div>
      </div>

      {/* General Settings */}
      <div className="glass rounded-2xl p-6 sm:p-8 mb-20 md:mb-0">
        <h2 className="text-2xl font-display font-semibold tracking-tight text-white mb-6">
          General Settings
        </h2>

        <div className="space-y-6">
          <div className="border-b border-white/10 pb-6">
            <label className="block text-white font-semibold mb-2">
              Business Timezone
            </label>
            <select className="w-full sm:w-64 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-cyan-500 focus:outline-none">
              <option>Australia/Sydney</option>
              <option>Australia/Melbourne</option>
              <option>Australia/Brisbane</option>
              <option>Australia/Perth</option>
              <option>Australia/Adelaide</option>
            </select>
            <p className="text-gray-400 text-sm mt-2">
              Used for all booking times and calendar sync
            </p>
          </div>

          <div className="border-b border-white/10 pb-6">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-white font-semibold mb-1">
                  Auto-sync Bookings
                </label>
                <p className="text-gray-400 text-sm">
                  Automatically create calendar events for confirmed bookings
                </p>
              </div>
              <input
                type="checkbox"
                defaultChecked
                className="w-6 h-6 rounded accent-cyan-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button className="px-6 py-2 glass glass-hover rounded-xl text-white font-semibold transition-all">
              Cancel
            </button>
            <button className="px-6 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-xl text-white font-semibold transition-all">
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
