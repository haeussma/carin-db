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
    PenBox,
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
import { ProjectSelector } from "@/components/layout/ProjectSelector"

export function DataManagerSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
    const pathname = usePathname();
    const { state, toggleSidebar } = useSidebar();
    const [showSettings, setShowSettings] = useState(false);
    const { theme, setTheme } = useTheme();

    const isActive = (path: string) => pathname === path;

    return (
        <Sidebar collapsible="icon" {...props}>
            <SidebarHeader className={state === "collapsed" ? "hidden" : ""}>
                <div className="px-2 py-2">
                    <ProjectSelector />
                </div>
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
                                        {/* <Link href="/edit">
                                            <Edit />
                                            <span>Edit</span>
                                        </Link> */}
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                                <SidebarMenuItem>
                                    <SidebarMenuButton asChild isActive={isActive("/new")} tooltip="Schema Designer">
                                        <Link href="/new">
                                            <PenBox />
                                            <span>Schema Editor</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </CollapsibleContent>
                        </Collapsible>

                        {/* Visualize */}
                        <SidebarMenuItem>
                            <SidebarMenuButton asChild isActive={isActive("/visualize")} tooltip="Visualize">
                                <Link href="/browser" target="_blank">
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
                <div className="flex justify-end items-center p-2">
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
        </Sidebar>
    );
}
