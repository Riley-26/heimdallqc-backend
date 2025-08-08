import React, { memo, useMemo } from "react"
import { useState, useEffect, useCallback } from "react"
import { WidgetComponent } from "../components/Widget"
import { WidgetConfig, UseWidgetResult, WidgetState, WatermarkProps, WidgetProps } from "../types"
import { apiService } from "../services/apiService"
import { WatermarkComponent } from "../components/Watermark"

export const useHMDL = (config: WidgetConfig): UseWidgetResult => {
    // Default configuration with fallbacks
    const widgetConfig: WidgetConfig = {
        apiKey: config.apiKey,
        darkTheme: config.darkTheme,
        initialOpen: config.initialOpen || false,
        onEvent: config.onEvent || (() => {}),
        watermarkSize: config.watermarkSize
    }

    // State management
    const [isOpen, setIsOpen] = useState<boolean>(widgetConfig.initialOpen || false)
    const [darkTheme, setDarkTheme] = useState<boolean>(true)
    const [showAlert, setShowAlert] = useState<boolean>(false)
    const [isLoading, setIsLoading] = useState<boolean>(false)
    const [confirmed, setConfirmed] = useState<boolean>(false)
    const [checked, setChecked] = useState<boolean>(false)
    const [error, setError] = useState<string | null>(null)

    // Combined state object
    const widgetState: WidgetState = {
        isOpen,
        confirmed,
        darkTheme,
        checked,
        isLoading,
        showAlert,
        setShowAlert,
    }

    // Widget control actions
    const widgetActions = {
        open: () => {
            setIsOpen(true)
            widgetConfig.onEvent?.("opened")
        },
        close: () => {
            setIsOpen(false)
            widgetConfig.onEvent?.("closed")
        },
        toggle: () => {
            setIsOpen((prev) => {
                const newState = !prev
                widgetConfig.onEvent?.(newState ? "opened" : "closed")
                return newState
            })
        },
        submit: async (data: string) => {
            if (confirmed) {
                const result = await createSubmission(data)
                widgetConfig.onEvent?.("submitted", data)
                return result
            } else {
                setShowAlert(true)
                setIsOpen(true)
            }
        },
        confirm: (state: boolean) => {
            setConfirmed(state)
            widgetConfig.onEvent?.(state ? "confirmed" : "unconfirmed", state)
        },
        check: (state: boolean) => {
            setChecked(state)
            widgetConfig.onEvent?.(state ? "checked" : "unchecked", state)
        },
        setDarkTheme: (isDark: boolean) => {
            setDarkTheme(isDark)
            widgetConfig.onEvent?.("theme_changed", isDark)
        },
    }

    // Create new submission
    const createSubmission = async (text: string) => {
        if (confirmed) {
            try {
                const submission = await apiService.createSubmission(text, widgetConfig.apiKey, checked, window.location.host, window.location.origin)
                const watermark = await createWatermark(submission)
                return {
                    "needsAction": false,
                    "modifiedText": ""
                }
            } catch (err: unknown) {
                if (err instanceof Error){
                    setError(err.message)
                } else {
                    setError("An error occurred")
                }
                return {
                    "needsAction": false
                }
            }
        }
    }

    const createWatermark = async (data:any) => {
        try {
            const watermark = await apiService.createWatermark(data, widgetConfig.apiKey)

            return watermark
        } catch (err: unknown) {
            if (err instanceof Error){
                setError(err.message)
            } else {
                setError("An error occurred")
            }
        }
    }

    const HMDLWidget = () => (
        <WidgetComponent
            config={widgetConfig}
            onClose={widgetActions.close}
            onOpen={widgetActions.open}
            onConfirm={widgetActions.confirm}
            onCheck={widgetActions.check}
            onSubmit={widgetActions.submit}
            widgetState={widgetState}
        />
    )

    const HMDLWatermark = (items: any) => (
        <WatermarkComponent items={items} size={widgetConfig.watermarkSize} />
    )

    return {
        HMDLWidget,
        widgetState,
        widgetActions,
        HMDLWatermark,
        isLoading,
        error,
    }
}
