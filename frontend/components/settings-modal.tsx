import React from 'react'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface SettingsModalProps {
    isOpen: boolean;
    setIsOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function SettingsModal({ isOpen, setIsOpen }: SettingsModalProps) {
    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon">
                    <span className="sr-only">Open settings</span>
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Settings</DialogTitle>
                    <DialogDescription>
                        Adjust your application settings here.
                    </DialogDescription>
                </DialogHeader>
                {/* Add your settings content here */}
            </DialogContent>
        </Dialog>
    )
} 