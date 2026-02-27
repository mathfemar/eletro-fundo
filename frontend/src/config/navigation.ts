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
        id: 'gestao',
        label: 'Gestão',
        basePath: '/simulador/gestao',
        navItems: [
            {
                label: 'Setup do Fundo',
                href: '/simulador/fundos/cadastro',
                icon: 'fas fa-file-circle-plus',
            },
            {
                label: 'Cotistas',
                href: '/simulador/cotistas',
                icon: 'fas fa-users',
            },
            {
                label: 'Carteiras e Alocação',
                href: '/simulador/alocacoes',
                icon: 'fas fa-wallet',
            },
        ],
    },
    {
        id: 'operacoes',
        label: 'Operações',
        basePath: '/simulador/operacoes',
        navItems: [
            {
                label: 'Operações',
                href: '/simulador/operacoes',
                icon: 'fas fa-right-left',
            },
            {
                label: 'Renda Fixa',
                href: '/simulador/renda-fixa',
                icon: 'fas fa-file-invoice-dollar',
            },
            {
                label: 'Aportes/Resgates',
                href: '/simulador/resgates',
                icon: 'fas fa-hand-holding-dollar',
            },
        ],
    },
    {
        id: 'visao',
        label: 'Visão',
        basePath: '/simulador/fundos',
        navItems: [
            {
                label: 'Visão Consolidada',
                href: '/simulador/fundos',
                icon: 'fas fa-building-columns',
            },
            {
                label: 'L · Carteiras',
                href: '/simulador/carteiras',
                icon: 'fas fa-wallet',
            },
            {
                label: 'L · Posições',
                href: '/simulador/posicoes',
                icon: 'fas fa-layer-group',
            },
        ],
    },
];
