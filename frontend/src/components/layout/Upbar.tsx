import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { sections } from '@/config/navigation';
import { useRefreshCache } from '@/hooks/usePrecos';
import './Upbar.css';

export default function Upbar() {
    const location = useLocation();
    const refresh = useRefreshCache();
    const [done, setDone] = useState(false);

    const upbarSections = sections.filter(s => s.id !== 'home');

    function handleRefresh() {
        setDone(false);
        refresh.mutate(undefined, {
            onSuccess: () => { setDone(true); setTimeout(() => setDone(false), 3000); },
        });
    }

    return (
        <header className="upbar">
            <nav className="upbar-sections">
                {upbarSections.map(section => {
                    const isActive = location.pathname.startsWith(section.basePath);
                    return (
                        <NavLink
                            key={section.id}
                            to={section.basePath}
                            className={`upbar-section-link${isActive ? ' active' : ''}`}
                        >
                            {section.label}
                        </NavLink>
                    );
                })}
            </nav>
            <div className="upbar-right">
                <button
                    className={`upbar-refresh-btn${done ? ' upbar-refresh-btn--done' : ''}`}
                    onClick={handleRefresh}
                    disabled={refresh.isPending}
                    title="Atualizar lista de ativos e preços live"
                >
                    <i className={`fas ${
                        refresh.isPending ? 'fa-circle-notch fa-spin' :
                        done ? 'fa-check' : 'fa-rotate-right'
                    }`} />
                    <span>{refresh.isPending ? 'Atualizando…' : done ? 'Atualizado!' : 'Atualizar Cache'}</span>
                </button>
                <span className="upbar-breadcrumb">F</span>
            </div>
        </header>
    );
}
