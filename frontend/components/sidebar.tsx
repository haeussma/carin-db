"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Home,
    Edit,
    PlusCircle,
    Search,
    HelpCircle,
    BarChart2,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    Settings,
    Sun,
    Moon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useState } from 'react'

import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuSub,
    SidebarMenuSubItem,
    SidebarMenuSubButton,
    SidebarRail,
    SidebarFooter,
    useSidebar,
} from "@/components/ui/sidebar";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { SettingsDialog } from "@/components/settings-dialog";
import {
    Sheet,
    SheetContent,
    SheetTrigger,
} from '@/components/ui/sheet'
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip'

export function DataManagerSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
    const pathname = usePathname();
    const { state, toggleSidebar } = useSidebar();
    const [showSettings, setShowSettings] = useState(false);
    const { theme, setTheme } = useTheme();

    const isActive = (path: string) => pathname === path;

    return (
        <Sidebar collapsible="icon" {...props}>
            <SidebarHeader className={state === "collapsed" ? "hidden" : ""}>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg">
                            <div className="flex flex-col gap-0.5 leading-none">
                                <span className="font-semibold">Data Manager</span>
                            </div>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarMenu>
                        {/* Home */}
                        <SidebarMenuItem>
                            <SidebarMenuButton asChild isActive={isActive("/home")} tooltip="Home">
                                <Link href="/home">
                                    <Home />
                                    <span>Home</span>
                                </Link>
                            </SidebarMenuButton>
                        </SidebarMenuItem>

                        {/* Collapsible Edit Section */}
                        <Collapsible defaultOpen>
                            <CollapsibleContent>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={isActive("/edit")} tooltip="Edit">
                                        <Link href="/edit">
                                            <Edit />
                                            <span>Edit</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </CollapsibleContent>
                        </Collapsible>

                        {/* Visualize */}
                        <SidebarMenuItem>
                            <SidebarMenuButton asChild isActive={isActive("/visualize")} tooltip="Visualize">
                                <Link href="/visualize">
                                    <BarChart2 />
                                    <span>Visualize</span>
                                </Link>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    </SidebarMenu>
                </SidebarGroup>
            </SidebarContent>
            <SidebarRail />
            <SidebarFooter>
                <div className="flex justify-between items-center p-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9"
                        onClick={() => setShowSettings(true)}
                        data-settings-button
                    >
                        <Settings className="h-4 w-4" />
                        <span className="sr-only">Settings</span>
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleSidebar}
                        className="rounded-full"
                    >
                        {state === "expanded" ? <ChevronLeft /> : <ChevronRight />}
                    </Button>
                </div>
            </SidebarFooter>
            <SettingsDialog
                open={showSettings}
                onOpenChange={setShowSettings}
            />
        </Sidebar>
    );
}
