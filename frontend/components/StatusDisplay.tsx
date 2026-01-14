'use client';

import React from 'react';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'failed';

interface StatusDisplayProps {
  status: ConnectionStatus;
  latency: number | null;
}

export function StatusDisplay({ status, latency }: StatusDisplayProps) {
  const getStatusConfig = (status: ConnectionStatus) => {
    switch (status) {
      case 'connected':
        return {
          bg: 'bg-gradient-to-r from-emerald-500 to-green-500',
          text: 'text-white',
          icon: '●',
          label: 'Connected',
          pulse: true,
        };
      case 'connecting':
        return {
          bg: 'bg-gradient-to-r from-amber-400 to-orange-500',
          text: 'text-white',
          icon: '⟳',
          label: 'Connecting...',
          pulse: true,
        };
      case 'failed':
        return {
          bg: 'bg-gradient-to-r from-red-500 to-rose-600',
          text: 'text-white',
          icon: '✕',
          label: 'Connection Failed',
          pulse: false,
        };
      case 'disconnected':
      default:
        return {
          bg: 'bg-slate-200',
          text: 'text-slate-700',
          icon: '○',
          label: 'Disconnected',
          pulse: false,
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-slate-200/50 p-6 sm:p-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${config.bg} ${config.pulse ? 'animate-pulse' : ''} shadow-lg`} />
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Connection Status</p>
              <p className={`text-lg font-semibold ${config.text === 'text-white' ? 'text-slate-800' : config.text}`}>
                {config.label}
              </p>
            </div>
          </div>
        </div>
        
        {status === 'connected' && latency !== null && (
          <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
            <div className="flex flex-col">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Network Latency</p>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  {latency}
                </span>
                <span className="text-sm font-medium text-slate-600">ms</span>
              </div>
            </div>
            <div className={`w-12 h-12 rounded-xl ${latency < 50 ? 'bg-emerald-100' : latency < 100 ? 'bg-amber-100' : 'bg-orange-100'} flex items-center justify-center`}>
              <svg className={`w-6 h-6 ${latency < 50 ? 'text-emerald-600' : latency < 100 ? 'text-amber-600' : 'text-orange-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

