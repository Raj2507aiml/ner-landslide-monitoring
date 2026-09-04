import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.warn('[ErrorBoundary Caught]', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs space-y-3 text-[var(--text-main)] my-2">
          <div className="flex items-center gap-2 text-rose-500 font-bold">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <span>Unable to render this module</span>
          </div>
          <p className="text-[11px] text-[var(--text-muted)]">
            A temporary component render error occurred. Your session and connection remain active.
          </p>
          <button
            onClick={this.handleReset}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-lg flex items-center gap-1.5 transition cursor-pointer text-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Reset View</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
