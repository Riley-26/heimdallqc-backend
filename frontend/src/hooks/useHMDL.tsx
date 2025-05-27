import React, { memo, useMemo } from 'react';
import { useState, useEffect, useCallback } from 'react';
import { HMDLWidget } from '../components/Widget';
import { WidgetConfig, UseWidgetResult, WidgetState } from '../types';

export const useHMDL = (config: WidgetConfig): UseWidgetResult => {
    // Default configuration with fallbacks
    const widgetConfig: WidgetConfig = {
        apiKey: config.apiKey,
        theme: config.theme || 'light',
        initialOpen: config.initialOpen || false,
        apiUrl: config.apiUrl || '/api',
        onEvent: config.onEvent || (() => { })
    };

    // State management
    const [isOpen, setIsOpen] = useState<boolean>(widgetConfig.initialOpen || false);
    const [theme, setTheme] = useState<'light' | 'dark'>(
        widgetConfig.theme === 'auto'
            ? window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
            : (widgetConfig.theme as 'light' | 'dark')
    );
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<Error | null>(null);
    const [content, setContent] = useState<string>()
    const [confirmed, setConfirmed] = useState<boolean>(false)

    // Combined state object
    const widgetState: WidgetState = {
        isOpen,
        confirmed,
        theme
    };

    // Load widget data from API
    const fetchData = useCallback(async (text:string) => {
        setIsLoading(true);
        setError(null);

        try {
            // Simulate API call
            const submissionResponse = await fetch(
                "http://127.0.0.1:8000/api/submissions",
                {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${widgetConfig.apiKey}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        text: text,
                        api_key: widgetConfig.apiKey,
                        source_url: window.location.href
                    })
                }
            )

            widgetConfig.onEvent?.('data_loaded', "Submitted");
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to fetch widget data'));
            widgetConfig.onEvent?.('error', err);
        } finally {
            setIsLoading(false);
        }
    }, [widgetConfig.apiKey, widgetConfig.apiUrl]);

    // Widget control actions
    const widgetActions = {
        open: () => {
            setIsOpen(true);
            widgetConfig.onEvent?.('opened');
        },
        close: () => {
            setIsOpen(false);
            widgetConfig.onEvent?.('closed');
        },
        toggle: () => {
            setIsOpen(prev => {
                const newState = !prev;
                widgetConfig.onEvent?.(newState ? 'opened' : 'closed');
                return newState;
            });
        },
        submit: async (data:string) => {
            console.log(data, 1)
            if (confirmed) {
                await fetchData(data)
            } else {
                console.log("please confirm")
            }
        },
        confirm: (confirmed:boolean) => {
            console.log(confirmed)
        },
        setText: (text:string) => {
            setContent(text)
        },
        setTheme: (newTheme: 'light' | 'dark') => {
            setTheme(newTheme);
            widgetConfig.onEvent?.('theme_changed', newTheme);
        }
    };

    // Widget component with required props
    const WidgetComponent = () => (
        <HMDLWidget 
            config= { widgetConfig }
            isOpen = { isOpen }
            onClose = { widgetActions.close }
            onOpen = { widgetActions.open }
            onConfirm = { widgetActions.confirm }
            onSubmit = { widgetActions.submit }
        />
    )

    return {
        WidgetComponent,
        widgetState,
        widgetActions,
        isLoading,
        error
    };
};