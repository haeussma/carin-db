'use client'

import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { SettingsCard } from "./settings-card"

interface SettingsDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Settings</DialogTitle>
                </DialogHeader>
                <SettingsCard onClose={() => onOpenChange(false)} />
            </DialogContent>
        </Dialog>
    )
} 