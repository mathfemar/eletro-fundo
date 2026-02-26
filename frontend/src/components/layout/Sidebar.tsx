import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { sections } from '@/config/navigation';
import type { NavItem } from '@/config/navigation';
import './Sidebar.css';

function NavItemComponent({ item, depth = 0 }: { item: NavItem; depth?: number }) {
    const location = useLocation();
    const hasChildren = item.children && item.children.length > 0;
    const isActive = !hasChildren && location.pathname === item.href;
    const isParentActive = hasChildren && item.children!.some(c => location.pathname.startsWith(c.href));
    const [open, setOpen] = useState(isParentActive);

    if (!hasChildren) {
        return (
            <NavLink to={item.href} className={`nav-item depth-${depth} ${isActive ? 'active' : ''}`}>
                <i className={`nav-icon ${item.icon}`} />
                <span>{item.label}</span>
            </NavLink>
        );
    }

    return (
        <div className="nav-group">
            <button
                className={`nav-item nav-toggle depth-${depth} ${isParentActive ? 'parent-active' : ''}`}
                onClick={() => setOpen(o => !o)}
            >
                <i className={`nav-icon ${item.icon}`} />
                <span>{item.label}</span>
                <i className={`nav-chevron fas fa-chevron-${open ? 'down' : 'right'}`} />
            </button>
            {open && (
                <div className="nav-children">
                    {item.children!.map(child => (
                        <NavItemComponent key={child.href} item={child} depth={depth + 1} />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function Sidebar() {
    const location = useLocation();
    // Evita que basePath '/' faça match em tudo com startsWith
    const currentSection =
        sections.find(s =>
            s.basePath === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(s.basePath)
        ) ?? sections[0];

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <NavLink to="/" className="sidebar-logo text-accent">F</NavLink>
            </div>
            <nav className="sidebar-nav">
                {currentSection.navItems.map(item => (
                    <NavItemComponent key={item.label} item={item} />
                ))}
            </nav>
            <div className="sidebar-footer">
                <span className="sidebar-version">v0.1.0</span>
            </div>
        </aside>
    );
}
