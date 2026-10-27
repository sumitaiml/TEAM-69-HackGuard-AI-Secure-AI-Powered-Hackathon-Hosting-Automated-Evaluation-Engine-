import React, { useState, useEffect } from 'react';
import { Monitor, Smartphone, Copy, Check, Sparkles, Laptop, ShieldAlert } from 'lucide-react';

interface DesktopOnlyGuardProps {
  children: React.ReactNode;
}

export function DesktopOnlyGuard({ children }: DesktopOnlyGuardProps) {
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [currentWidth, setCurrentWidth] = useState<number>(window.innerWidth);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    const checkMobile = () => {
      const width = window.innerWidth;
      setCurrentWidth(width);

      // Check user agent for common mobile and tablet devices
      const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera || '';
      const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i.test(userAgent);
      
      // Screen width breakpoint: HackEval sidebars, dual-pane diffs & judge consoles require at least 1024px
      const isSmallScreen = width < 1024;

      setIsMobile(isMobileUA || isSmallScreen);
    };

    // Initial check
    checkMobile();

    // Listen to resize and orientation change events
    window.addEventListener('resize', checkMobile);
    window.addEventListener('orientationchange', checkMobile);

    return () => {
      window.removeEventListener('resize', checkMobile);
      window.removeEventListener('orientationchange', checkMobile);
    };
  }, []);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (!isMobile) {
    return <>{children}</>;
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: '#0F1012',
        color: '#FFFFFF',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 20px',
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        position: 'relative',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Background ambient lighting */}
      <div
        style={{
          position: 'absolute',
          top: '-15%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '320px',
          height: '320px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(43, 127, 255, 0.22) 0%, rgba(43, 127, 255, 0) 70%)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: '-10%',
          right: '-10%',
          width: '280px',
          height: '280px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.18) 0%, rgba(139, 92, 246, 0) 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Main Container Card */}
      <div
        style={{
          maxWidth: '480px',
          width: '100%',
          backgroundColor: '#18191C',
          border: '1px solid #2D3039',
          borderRadius: '28px',
          padding: '36px 28px',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), 0 1px 2px rgba(255, 255, 255, 0.05)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          position: 'relative',
          zIndex: 1,
          animation: 'fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        }}
      >
        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '10px',
              backgroundColor: '#2B7FFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(43, 127, 255, 0.35)',
            }}
          >
            <Sparkles size={18} color="#FFFFFF" />
          </div>
          <span style={{ fontSize: '18px', fontWeight: '800', letterSpacing: '-0.02em', color: '#FFFFFF' }}>
            HackEval
          </span>
          <span
            style={{
              fontSize: '11px',
              fontWeight: '700',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              color: '#9CA3AF',
              padding: '3px 8px',
              borderRadius: '99px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            v1.0 Live
          </span>
        </div>

        {/* Visual Device Illustration */}
        <div
          style={{
            position: 'relative',
            width: '120px',
            height: '84px',
            marginBottom: '26px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* Laptop / Monitor Graphic */}
          <div
            style={{
              width: '88px',
              height: '60px',
              borderRadius: '10px',
              backgroundColor: '#22252C',
              border: '2px solid #2B7FFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(43, 127, 255, 0.25)',
            }}
          >
            <Laptop size={34} color="#2B7FFF" />
          </div>

          {/* Smartphone Restricted Indicator */}
          <div
            style={{
              position: 'absolute',
              bottom: '-2px',
              right: '2px',
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: '#EF4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '3px solid #18191C',
              boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)',
            }}
          >
            <Smartphone size={18} color="#FFFFFF" />
          </div>
        </div>

        {/* Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#F87171',
            padding: '6px 14px',
            borderRadius: '99px',
            fontSize: '12px',
            fontWeight: '700',
            marginBottom: '16px',
            letterSpacing: '0.02em',
          }}
        >
          <ShieldAlert size={14} />
          <span>Desktop Experience Only</span>
        </div>

        {/* Title */}
        <h1
          style={{
            fontSize: '22px',
            fontWeight: '800',
            lineHeight: '1.3',
            color: '#FFFFFF',
            marginBottom: '12px',
            letterSpacing: '-0.02em',
          }}
        >
          Please Open on a Laptop or Desktop
        </h1>

        {/* Description */}
        <p
          style={{
            fontSize: '14px',
            lineHeight: '1.6',
            color: '#9CA3AF',
            marginBottom: '24px',
          }}
        >
          HackEval includes full split-pane AST code inspection, live AI agent execution streams, slide deck critiques, and organizer scoreboards designed specifically for widescreen displays.
        </p>

        {/* Requirements Box */}
        <div
          style={{
            width: '100%',
            backgroundColor: '#1E2026',
            border: '1px solid #2B2E38',
            borderRadius: '16px',
            padding: '16px 18px',
            marginBottom: '24px',
            textAlign: 'left',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: '700', color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
            Workstation Requirements
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: '#E5E7EB' }}>
              <Monitor size={15} color="#2B7FFF" />
              <span>Recommended resolution: <strong>1024px width</strong> or higher</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: '#E5E7EB' }}>
              <Laptop size={15} color="#10B981" />
              <span>Compatible with Chrome, Edge, Safari, Firefox</span>
            </div>
          </div>
        </div>

        {/* Action Button: Copy Link */}
        <button
          onClick={handleCopyLink}
          style={{
            width: '100%',
            backgroundColor: copied ? '#10B981' : '#2B7FFF',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '99px',
            padding: '14px 20px',
            fontSize: '14px',
            fontWeight: '700',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            boxShadow: copied ? '0 4px 14px rgba(16, 185, 129, 0.3)' : '0 4px 16px rgba(43, 127, 255, 0.35)',
            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          {copied ? (
            <>
              <Check size={16} />
              <span>Link Copied! Send to Your PC</span>
            </>
          ) : (
            <>
              <Copy size={16} />
              <span>Copy Link to Open on Desktop</span>
            </>
          )}
        </button>

        {/* Viewport Diagnostic Note */}
        <div
          style={{
            marginTop: '18px',
            fontSize: '11px',
            color: '#6B7280',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>Detected screen: <strong>{currentWidth}px</strong> width (min required: 1024px)</span>
        </div>
      </div>

      {/* Footer Branding */}
      <div
        style={{
          marginTop: '24px',
          fontSize: '12px',
          color: '#4B5563',
          zIndex: 1,
        }}
      >
        © 2026 HackEval Platform • Secure AI Hackathon Engine
      </div>
    </div>
  );
}

