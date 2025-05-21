import React from 'react';
import { WidgetProps } from '../types';
import '../styles/widget.css';

export const HMDLWidget: React.FC<WidgetProps> = ({
    config,
    isOpen = false,
    content = "",
    onClose,
    onOpen,
    onSubmit
}) => {
    // Theme class
    const themeClass = `widget--${config.theme === 'auto'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : (config.theme || 'light')}`;

    return (
        <div className={`widget-container`}>
            {/* Widget Button */}
            <button
                className="widget-button"
                onClick={() => isOpen ? onClose?.() : onOpen?.()}
                aria-expanded={isOpen}
                aria-label={isOpen ? "Close widget" : "Open widget"}
            >
                {isOpen ? 'X' : '?'}
            </button>

            {/* Widget Content */}
            {isOpen && (
                <div className={`widget ${themeClass}`}>
                    <div className="widget-header">
                        <h3>Widget</h3>
                        <button
                            className="widget-close-button"
                            onClick={() => onClose?.()}
                            aria-label="Close widget"
                        >
                            x
                        </button>
                    </div>

                    <div className="widget-content">
                        <p>This is a customizable widget.</p>
                        <p>API Key: {config.apiKey.substring(0, 4)}...</p>
                    </div>

                    <div className="widget-footer">
                        <p>Widget Footer</p>
                        <button onClick={() => {onSubmit?.(content)}}>Button</button>
                    </div>
                </div>
            )}
        </div>
    );
};