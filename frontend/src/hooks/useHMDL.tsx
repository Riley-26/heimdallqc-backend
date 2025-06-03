import React, { memo, useMemo } from 'react';
import { useState, useEffect, useCallback } from 'react';
import { HMDLWidget } from '../components/Widget';
import { WidgetConfig, UseWidgetResult, WidgetState } from '../types';

export const useHMDL = (config: WidgetConfig): UseWidgetResult => {
    // Default configuration with fallbacks
    const widgetConfig: WidgetConfig = {
        apiKey: config.apiKey,
        darkTheme: config.darkTheme,
        initialOpen: config.initialOpen || false,
        onEvent: config.onEvent || (() => { })
    };

    // State management
    const [isOpen, setIsOpen] = useState<boolean>(widgetConfig.initialOpen || false);
    const [darkTheme, setDarkTheme] = useState<boolean>(true);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<Error | null>(null);
    const [content, setContent] = useState<string>()
    const [confirmed, setConfirmed] = useState<boolean>(false)
    const [checked, setChecked] = useState<boolean>(false)

    // Combined state object
    const widgetState: WidgetState = {
        isOpen,
        confirmed,
        darkTheme,
        checked
    };

    // Load widget data from API
    const fetchData = async (text: string) => {
        setIsLoading(true);
        setError(null);

        if (text){
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
                setError(err instanceof Error ? err : new Error('Failed to analyse submitted data'));
                widgetConfig.onEvent?.('error', err);
            } finally {
                setIsLoading(false);
            }
        }
    };

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
        submit: async (data: string) => {
            console.log(data)
            if (confirmed) {
                await fetchData(data)
                widgetConfig.onEvent?.("submitted", data);
            } else {
                console.log("please confirm")
            }
        },
        confirm: (state: boolean) => {
            setConfirmed(state)
            widgetConfig.onEvent?.(state ? "confirmed": "unconfirmed", state);
        },
        check: (state: boolean) => {
            setChecked(state)
            widgetConfig.onEvent?.(state ? "checked": "unchecked", state);
        },
        setDarkTheme: (isDark: boolean) => {
            setDarkTheme(isDark);
            widgetConfig.onEvent?.('theme_changed', isDark);
        }
    };

    // Widget component with required props
    const WidgetComponent = () => (
        <HMDLWidget
            config={widgetConfig}
            onClose={widgetActions.close}
            onOpen={widgetActions.open}
            onConfirm={widgetActions.confirm}
            onCheck={widgetActions.check}
            onSubmit={widgetActions.submit}
            widgetState={widgetState}
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