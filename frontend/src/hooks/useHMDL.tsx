import React from 'react';
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
    const [data, setData] = useState<any | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<Error | null>(null);
    const [content, setContent] = useState<string>()

    // Combined state object
    const widgetState: WidgetState = {
        isOpen,
        theme,
        data
    };

    // Load widget data from API
    const fetchData = useCallback(async () => {
        // In a real implementation, this would call the API
        // For now, we'll just simulate data loading
        setIsLoading(true);
        setError(null);

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            // Mock data
            setData({
                title: "Widget Demo",
                content: "This is a demo widget"
            });

            widgetConfig.onEvent?.('data_loaded', data);
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to fetch widget data'));
            widgetConfig.onEvent?.('error', err);
        } finally {
            setIsLoading(false);
        }
    }, [widgetConfig.apiKey, widgetConfig.apiUrl]);

    // Load data on initial render
    useEffect(() => {
        fetchData();
    }, [fetchData]);

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
        submit: (data:string) => {
            console.log(data, 1)
        },
        setText: (text:string) => {
            setContent(text)
        },
        setTheme: (newTheme: 'light' | 'dark') => {
            setTheme(newTheme);
            widgetConfig.onEvent?.('theme_changed', newTheme);
        },
        refresh: async () => {
            widgetConfig.onEvent?.('refresh_requested');
            await fetchData();
            return;
        }
    };

    // Widget component with required props
    const WidgetComponent = () => (
        <HMDLWidget 
            config= { widgetConfig }
            isOpen = { isOpen }
            onClose = { widgetActions.close }
            onOpen = { widgetActions.open }
            content = { content }
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