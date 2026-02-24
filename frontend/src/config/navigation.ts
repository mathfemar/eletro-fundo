export interface NavItem {
    label: string;
    href: string;
    icon: string;          // classe Font Awesome
    children?: NavItem[];
}

export interface Section {
    id: string;
    label: string;
    basePath: string;
    navItems: NavItem[];
}

export const sections: Section[] = [
    {
        id: 'home',
        label: 'Início',
        basePath: '/',
        navItems: [
            {
                label: 'Página Inicial',
                href: '/',
                icon: 'fas fa-home',
            },
        ],
    },
    {
        id: 'ativos',
        label: 'Ativos',
        basePath: '/ativos',
        navItems: [
            {
                label: 'Consulta/Cadastro',
                href: '/ativos/lista',
                icon: 'fas fa-folder-open',
            },
            {
                label: 'Preços ao Vivo',
                href: '/ativos/precos-ao-vivo',
                icon: 'fas fa-bolt',
            },
            {
                label: 'Histórico de Preços',
                href: '/ativos/historico',
                icon: 'fas fa-chart-line',
            },
        ],
    },
    {
        id: 'simulador',
        label: 'Simulador',
        basePath: '/simulador',
        navItems: [
            {
                label: 'Visão Geral',
                href: '/simulador',
                icon: 'fas fa-flask',
            },
            {
                label: 'Carteiras',
                href: '/simulador/carteiras',
                icon: 'fas fa-wallet',
            },
            {
                label: 'Operações',
                href: '/simulador/operacoes',
                icon: 'fas fa-right-left',
            },
            {
                label: 'Posições',
                href: '/simulador/posicoes',
                icon: 'fas fa-layer-group',
            },
            {
                label: 'Fundos',
                href: '/simulador/fundos',
                icon: 'fas fa-building-columns',
            },
        ],
    },
];
