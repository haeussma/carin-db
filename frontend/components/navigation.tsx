"use client"

import * as React from "react"
import Link from "next/link"

import { cn } from "@/lib/utils"
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
    navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu"

const components: { title: string; href: string; description: string }[] = [
    {
        title: "Alert Dialog",
        href: "/docs/primitives/alert-dialog",
        description:
            "A modal dialog that interrupts the user with important content and expects a response.",
    },
    {
        title: "Hover Card",
        href: "/docs/primitives/hover-card",
        description:
            "For sighted users to preview content available behind a link.",
    },
    {
        title: "Progress",
        href: "/docs/primitives/progress",
        description:
            "Displays an indicator showing the completion progress of a task, typically displayed as a progress bar.",
    },
    {
        title: "Scroll-area",
        href: "/docs/primitives/scroll-area",
        description: "Visually or semantically separates content.",
    },
    {
        title: "Tabs",
        href: "/docs/primitives/tabs",
        description:
            "A set of layered sections of content—known as tab panels—that are displayed one at a time.",
    },
    {
        title: "Tooltip",
        href: "/docs/primitives/tooltip",
        description:
            "A popup that displays information related to an element when the element receives keyboard focus or the mouse hovers over it.",
    },
]

export function NavigationMenuDemo() {
    return (
        <NavigationMenu>
            <NavigationMenuList>
                {/* Home */}
                <NavigationMenuItem>
                    <NavigationMenuLink asChild>
                        <Link href="/home" className={navigationMenuTriggerStyle()}>
                            Home
                        </Link>
                    </NavigationMenuLink>
                </NavigationMenuItem>

                {/* "Edit" Dropdown */}
                <NavigationMenuItem>
                    <NavigationMenuTrigger>
                        <Link href="/edit" className={navigationMenuTriggerStyle()}>
                            Edit
                        </Link>
                    </NavigationMenuTrigger>
                    <NavigationMenuContent>
                        <ul className="flex flex-col gap-3 p-4 min-w-[300px]">
                            <ListItem href="/edit#add-data" title="Add Data">
                                Add data to your knowledgebase.
                            </ListItem>
                            <ListItem href="/edit#ask" title="Ask">
                                Ask questions about your knowledgebase.
                            </ListItem>
                            <ListItem href="/edit#convert" title="Convert">
                                Convert data from your knowledgebase to a standard format.
                            </ListItem>
                        </ul>
                    </NavigationMenuContent>
                </NavigationMenuItem>

                {/* Visualize */}
                <NavigationMenuItem>
                    <NavigationMenuLink asChild>
                        <Link href="/docs" className={navigationMenuTriggerStyle()}>
                            Visualize
                        </Link>
                    </NavigationMenuLink>
                </NavigationMenuItem>
            </NavigationMenuList>
        </NavigationMenu>
    )
}

interface ListItemProps extends React.ComponentPropsWithoutRef<"a"> {
    title: string
    href: string  // Make href required and string type
}

const ListItem = React.forwardRef<
    React.ElementRef<"a">,
    ListItemProps
>(({ className, title, children, href, ...props }, ref) => {
    return (
        <li>
            <NavigationMenuLink asChild>
                <Link
                    ref={ref as any} // Type assertion needed due to forwarded ref
                    href={href}  // Now href is guaranteed to be a string
                    className={cn(
                        "block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
                        className
                    )}
                    {...props}
                >
                    <div className="text-sm font-medium leading-none">{title}</div>
                    <div className="line-clamp-2 text-sm leading-snug text-muted-foreground">
                        {children}
                    </div>
                </Link>
            </NavigationMenuLink>
        </li>
    )
})
ListItem.displayName = "ListItem"
