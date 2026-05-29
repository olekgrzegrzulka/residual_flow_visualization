import collections
import copy
import math
import os
import sys
import tkinter as tk
from tkinter import filedialog

import pygame
import pygame.gfxdraw
from pygame.math import clamp
from typing_extensions import LiteralString

# Init
root = tk.Tk()
root.withdraw()


# BACKEND
class Graph:
    def __init__(self, graph):
        self.graph = copy.deepcopy(graph)
        self.row = len(graph)

    def bfs(self, s, t, parent):
        visited = [False] * self.row
        queue = collections.deque()
        queue.append(s)
        visited[s] = True

        while queue:
            u = queue.popleft()
            for ind, val in enumerate(self.graph[u]):
                if not visited[ind] and val > 0:
                    queue.append(ind)
                    visited[ind] = True
                    parent[ind] = u
        return visited[t]

    def edmonds_karp(self, source, sink):
        parent = [-1] * self.row
        max_flow = 0
        ret_arr = []

        while self.bfs(source, sink, parent):
            path_flow = float("Inf")
            s = sink
            current_path = []

            while s != source:
                path_flow = min(path_flow, self.graph[parent[s]][s])
                current_path.append(s)
                s = parent[s]
            current_path.append(source)
            current_path.reverse()

            ret_arr.append((current_path, path_flow))
            max_flow += path_flow

            v = sink
            while v != source:
                u = parent[v]
                self.graph[u][v] -= path_flow
                self.graph[v][u] += path_flow
                v = parent[v]

        return max_flow, ret_arr


# FRONTEND
pygame.init()
WIDTH, HEIGHT = 1100, 800
PANEL_WIDTH = 250
WORK_WIDTH = WIDTH - PANEL_WIDTH
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wizualizacja Algorytmu Edmondsa-Karpa")

if os.path.exists("font.ttf"):
    font = pygame.font.Font("font.ttf", 16)
    font.set_bold(True)
    large_font = pygame.font.Font("font.ttf", 24)
    large_font.set_bold(True)
else:
    print("Nie znaleziono pliku font.ttf")
    font = pygame.font.SysFont("Segoe UI", 15, bold=True)
    large_font = pygame.font.SysFont("Segoe UI", 24, bold=True)

# Paleta kolorów
BG_COLOR = (22, 24, 28)
GRID_COLOR = (35, 38, 45)
NODE_COLOR = (88, 166, 255)
SOURCE_COLOR = (46, 160, 67)
SINK_COLOR = (248, 81, 73)
TEXT_COLOR = (230, 237, 243)
EDGE_COLOR = (139, 148, 158)

BTN_INACTIVE = (48, 54, 61)
BTN_HOVER = (70, 78, 88)
BTN_ACTIVE = (100, 110, 120)

BTN_GREEN = (45, 110, 60)
BTN_GREEN_HOVER = (55, 130, 70)

BTN_RED = (140, 50, 50)
BTN_RED_HOVER = (160, 60, 60)

# Stany
nodes = []
edges = {}
mode = "ADD_NODE"
selected_node = None
dragging_node = None
is_dragging = False
drag_start_pos = (0, 0)
source_node = 0
sink_node = None
input_weight_str = ""
target_node = None
max_flow_result = 0
flow_paths = []

error_msg_time = -2500
error_msg_text = ""

colors = [
    (255, 123, 114),
    (121, 192, 255),
    (210, 168, 255),
    (242, 204, 96),
    (86, 211, 100),
    (67, 206, 224),
]

hints = {
    "ADD_NODE": "Kliknij na pustą siatkę, aby dodać wierchułek.",
    "DELETE": "Kliknij na wierchułek lub krawędź, aby usunąć element.",
    "ADD_EDGE": "Kliknij wierchułek początkowy, a następnie końcowy.",
    "SET_SRC": "Kliknij wierchułek, aby ustawić jako źródło (IN).",
    "SET_SINK": "Kliknij wierchułek, aby ustawić jako ujście (OUT).",
    "INPUT_WEIGHT": "Wpisz wagę i wciśnij Enter (domyślnie 1). Esc anuluje.",
}


def point_to_segment_dist(p, v, w):
    l2 = (v[0] - w[0]) ** 2 + (v[1] - w[1]) ** 2
    if l2 == 0:
        return math.hypot(p[0] - v[0], p[1] - v[1])
    t = max(
        0, min(1, ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2)
    )
    proj = (v[0] + t * (w[0] - v[0]), v[1] + t * (w[1] - v[1]))
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def draw_arrow(surface, color, start, end, offset=0, width=2):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return

    dx /= length
    dy /= length
    nx, ny = -dy, dx

    sx = start[0] + nx * offset
    sy = start[1] + ny * offset
    ex = end[0] + nx * offset - dx * 22
    ey = end[1] + ny * offset - dy * 22

    pygame.draw.aaline(surface, color, (sx, sy), (ex, ey))
    if width > 1:
        pygame.draw.aaline(surface, color, (sx + nx, sy + ny), (ex + nx, ey + ny))
        pygame.draw.aaline(surface, color, (sx - nx, sy - ny), (ex - nx, ey - ny))

    arrow_size = 12
    angle = math.atan2(dy, dx)
    p1x = ex - arrow_size * math.cos(angle - math.pi / 6)
    p1y = ey - arrow_size * math.sin(angle - math.pi / 6)
    p2x = ex - arrow_size * math.cos(angle + math.pi / 6)
    p2y = ey - arrow_size * math.sin(angle + math.pi / 6)

    points = [(int(ex), int(ey)), (int(p1x), int(p1y)), (int(p2x), int(p2y))]
    pygame.gfxdraw.aapolygon(surface, points, color)
    pygame.gfxdraw.filled_polygon(surface, points, color)


def run_algorithm() -> LiteralString | None:
    global max_flow_result, flow_paths
    if (
        not nodes
        or source_node is None
        or sink_node is None
        or sink_node == source_node
    ):
        return "Nie dodano żadnych punktów lub nie ustawiono źródła/ujścia!"
    size = len(nodes)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for (u, v), w in edges.items():
        matrix[u][v] = w
    g = Graph(matrix)
    if source_node != sink_node:
        max_flow_result, flow_paths = g.edmonds_karp(source_node, sink_node)
        if not flow_paths:
            return "Brak ścieżek przepływu między źródłem a ujściem!"
    return None


def save_to_file():
    filepath = filedialog.asksaveasfilename(
        defaultextension=".txt", filetypes=[("Text files", "*.txt")]
    )
    if not filepath:
        return
    size = len(nodes)
    matrix = [[0.0] * size for _ in range(size)]
    for (u, v), w in edges.items():
        matrix[u][v] = w
    with open(filepath, "w") as f:
        f.write(f"{source_node if source_node is not None else -1}\n")
        f.write(f"{sink_node if sink_node is not None else -1}\n")

        for row in matrix:
            f.write(",".join(map(str, row)) + "\n")


def load_from_file():
    global source_node, sink_node, error_msg_time, error_msg_text, nodes, edges
    filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError("Nie znaleziono pliku!")

    try:
        with open(filepath, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        if not lines:
            raise ValueError("Plik jest pusty!")

        if len(lines) >= 2 and "," not in lines[0] and "," not in lines[1]:
            saved_src = int(lines.pop(0))
            saved_sink = int(lines.pop(0))
            source_node = saved_src if saved_src != -1 else None
            sink_node = saved_sink if saved_sink != -1 else None
        else:
            source_node = 0 if len(lines) > 0 else None
            sink_node = len(lines) - 1 if len(lines) > 0 else None

        matrix = [list(map(float, line.split(","))) for line in lines]
        size = len(matrix)

        if any(len(row) != size for row in matrix):
            raise ValueError("Macierz nie jest kwadratowa!")

        temp_nodes = []
        temp_edges = {}
        center_x = WORK_WIDTH // 2
        center_y = HEIGHT // 2
        radius = min(WORK_WIDTH, HEIGHT) // 3

        if any(matrix[i][j] < 0 for i in range(size) for j in range(size)):
            raise ValueError("Wagi krawędzi muszą być dodatnie!")

        for i in range(size):
            angle = 2 * math.pi * i / size
            temp_nodes.append(
                [
                    int(center_x + radius * math.cos(angle)),
                    int(center_y + radius * math.sin(angle)),
                ]
            )
            for j in range(size):
                if matrix[i][j] > 0:
                    temp_edges[(i, j)] = matrix[i][j]

        nodes.clear()
        edges.clear()
        nodes.extend(temp_nodes)
        edges.update(temp_edges)

    except Exception as _e:
        error_msg_text = "Błąd pliku: Niepoprawna macierz lub format!"
        error_msg_time = pygame.time.get_ticks()


def get_clicked_node(pos, radius=20):
    for i, n_pos in enumerate(nodes):
        if math.hypot(n_pos[0] - pos[0], n_pos[1] - pos[1]) < radius:
            return i
    return None


def draw_text_centered(surface, text, font, color, rect):
    txt_surf = font.render(text, True, color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)


# Układ panelu bocznego
col_x = WORK_WIDTH + 25
btn_w, btn_h = 200, 32

y_akcje = 50
y_konf = 240
y_sym = 380
y_proj = 520

tools_btns = {
    "ADD_NODE": pygame.Rect(col_x, y_akcje, btn_w, btn_h),
    "ADD_EDGE": pygame.Rect(col_x, y_akcje + 42, btn_w, btn_h),
    "DELETE": pygame.Rect(col_x, y_akcje + 84, btn_w, btn_h),
    "SET_SRC": pygame.Rect(col_x, y_konf, btn_w, btn_h),
    "SET_SINK": pygame.Rect(col_x, y_konf + 42, btn_w, btn_h),
}

action_btns = {
    "RUN": pygame.Rect(col_x, y_sym, btn_w, btn_h),
    "CLEAR_SIM": pygame.Rect(col_x, y_sym + 42, btn_w, btn_h),
    "LOAD": pygame.Rect(col_x, y_proj, btn_w, btn_h),
    "SAVE": pygame.Rect(col_x, y_proj + 42, btn_w, btn_h),
    "CLEAR": pygame.Rect(col_x, y_proj + 84, btn_w, btn_h),
}

labels = {
    "ADD_NODE": "Dodaj Wierchułek",
    "ADD_EDGE": "Dodaj Krawędź",
    "DELETE": "Usuń Wierchułek/Krawędź",
    "SET_SRC": "Ustaw źródło",
    "SET_SINK": "Ustaw ujście",
    "RUN": "Uruchom",
    "CLEAR_SIM": "Wyczyść symulację",
    "LOAD": "Wczytaj z pliku",
    "SAVE": "Zapisz do pliku",
    "CLEAR": "Wyczyść projekt",
}

headers = [
    ("Akcje", col_x + btn_w // 2, y_akcje - 25),
    ("Punkty skrajne", col_x + btn_w // 2, y_konf - 25),
    ("Symulacja", col_x + btn_w // 2, y_sym - 25),
    ("Projekt", col_x + btn_w // 2, y_proj - 25),
]


def get_btn_color(key, mode, is_hover):
    if key in tools_btns and key == mode:
        return BTN_ACTIVE
    if key == "RUN":
        return BTN_GREEN_HOVER if is_hover else BTN_GREEN
    if key == "CLEAR":
        return BTN_RED_HOVER if is_hover else BTN_RED
    if key == "DELETE":
        return (
            (
                (BTN_INACTIVE[0] * 2 + BTN_RED[0]) // 3,
                (BTN_INACTIVE[1] * 2 + BTN_RED[1]) // 3,
                (BTN_INACTIVE[2] * 2 + BTN_RED[2]) // 3,
            )
            if not is_hover
            else (
                (BTN_HOVER[0] * 2 + BTN_RED_HOVER[0]) // 3,
                (BTN_HOVER[1] * 2 + BTN_RED_HOVER[1]) // 3,
                (BTN_HOVER[2] * 2 + BTN_RED_HOVER[2]) // 3,
            )
        )
    return BTN_HOVER if is_hover else BTN_INACTIVE


running = True
clock = pygame.time.Clock()

while running:
    mouse_pos = pygame.mouse.get_pos()
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if (
                event.button == 1
                and mode != "INPUT_WEIGHT"
                and event.pos[0] < WORK_WIDTH
            ):
                clicked_node = get_clicked_node(event.pos)
                if clicked_node is not None:
                    dragging_node = clicked_node
                    drag_start_pos = event.pos
                    is_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if dragging_node is not None and mode != "INPUT_WEIGHT":
                if (
                    math.hypot(
                        event.pos[0] - drag_start_pos[0],
                        event.pos[1] - drag_start_pos[1],
                    )
                    > 5
                ):
                    is_dragging = True

                new_x = min(max(20, event.pos[0]), WORK_WIDTH - 20)
                new_y = min(max(20, event.pos[1]), HEIGHT - 20)
                nodes[dragging_node] = [new_x, new_y]

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and mode != "INPUT_WEIGHT":
                clicked_ui = False
                for key, rect in {**tools_btns, **action_btns}.items():
                    if rect.collidepoint(event.pos) and not is_dragging:
                        clicked_ui = True
                        if key == "RUN":
                            error = run_algorithm()
                            if error is not None:
                                error_msg_text = error
                                error_msg_time = current_time
                        elif key == "CLEAR_SIM":
                            flow_paths.clear()
                            max_flow_result = 0
                        elif key == "CLEAR":
                            nodes.clear()
                            edges.clear()
                            flow_paths.clear()
                            max_flow_result = 0
                            source_node = None
                            sink_node = None
                        elif key == "SAVE":
                            try:
                                save_to_file()
                            except Exception as _e:
                                error_msg_text = "Bład zapisu pliku"
                                error_msg_time = current_time
                        elif key == "LOAD":
                            try:
                                load_from_file()
                                flow_paths.clear()
                                max_flow_result = 0
                            except Exception as _e:
                                error_msg_text = "Bład wczytywania pliku"
                                error_msg_time = current_time
                        else:
                            if mode == key:
                                mode = ""
                            else:
                                mode = key
                            selected_node = None
                        break

                if not clicked_ui and event.pos[0] < WORK_WIDTH:
                    clicked_node = get_clicked_node(event.pos)

                    if not is_dragging:
                        if mode == "ADD_NODE" and clicked_node is None:
                            flow_paths.clear()
                            max_flow_result = 0
                            nodes.append(list(event.pos))
                            if source_node is None:
                                source_node = len(nodes) - 1
                            elif sink_node is None and len(nodes) > 1:
                                sink_node = len(nodes) - 1

                        elif mode == "DELETE":
                            if clicked_node is not None:
                                flow_paths.clear()
                                max_flow_result = 0
                                nodes.pop(clicked_node)
                                new_edges = {}
                                for (u, v), w in edges.items():
                                    if u == clicked_node or v == clicked_node:
                                        continue
                                    new_u = u if u < clicked_node else u - 1
                                    new_v = v if v < clicked_node else v - 1
                                    new_edges[(new_u, new_v)] = w
                                edges = new_edges
                                if source_node == clicked_node:
                                    source_node = None
                                elif (
                                    source_node is not None
                                    and source_node > clicked_node
                                ):
                                    source_node -= 1
                                if sink_node == clicked_node:
                                    sink_node = None
                                elif sink_node is not None and sink_node > clicked_node:
                                    sink_node -= 1
                            else:
                                for u, v in list(edges.keys()):
                                    offset = 12 if (v, u) in edges else 0
                                    dx, dy = (
                                        nodes[v][0] - nodes[u][0],
                                        nodes[v][1] - nodes[u][1],
                                    )
                                    length = math.hypot(dx, dy)
                                    if length > 0:
                                        nx, ny = -dy / length, dx / length
                                        p1 = (
                                            nodes[u][0] + nx * offset,
                                            nodes[u][1] + ny * offset,
                                        )
                                        p2 = (
                                            nodes[v][0] + nx * offset,
                                            nodes[v][1] + ny * offset,
                                        )
                                        if (
                                            point_to_segment_dist(event.pos, p1, p2)
                                            < 10
                                        ):
                                            flow_paths.clear()
                                            max_flow_result = 0
                                            del edges[(u, v)]
                                            break

                        elif mode == "ADD_EDGE" and clicked_node is not None:
                            if selected_node is None:
                                selected_node = clicked_node
                            elif selected_node != clicked_node:
                                mode = "INPUT_WEIGHT"
                                target_node = clicked_node
                                input_weight_str = ""

                        elif mode == "SET_SRC" and clicked_node is not None:
                            flow_paths.clear()
                            max_flow_result = 0
                            source_node = clicked_node
                        elif mode == "SET_SINK" and clicked_node is not None:
                            flow_paths.clear()
                            max_flow_result = 0
                            sink_node = clicked_node

                dragging_node = None
                is_dragging = False

        elif event.type == pygame.KEYDOWN:
            if mode == "INPUT_WEIGHT":
                if event.key == pygame.K_ESCAPE:
                    mode = "ADD_EDGE"
                    selected_node = None
                    input_weight_str = ""
                elif event.key == pygame.K_RETURN:
                    try:
                        weight = (
                            1.0 if input_weight_str == "" else float(input_weight_str)
                        )
                        if weight > 0:
                            flow_paths.clear()
                            max_flow_result = 0
                            weight = clamp(weight, 2 ** (-4), 2**28)
                            edges[(selected_node, target_node)] = weight
                        else:
                            raise ValueError("Waga musi być dodatnia!")
                        mode = "ADD_EDGE"
                        selected_node = None
                    except ValueError:
                        error_msg_text = "Wprowadzono złą wartość!"
                        error_msg_time = current_time
                        input_weight_str = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_weight_str = input_weight_str[:-1]
                elif event.unicode.isprintable():
                    input_weight_str += event.unicode
            elif mode == "ADD_EDGE" and selected_node is not None:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
                    selected_node = None

    # Kursor
    cursor = pygame.SYSTEM_CURSOR_ARROW
    is_hovering_ui = any(
        rect.collidepoint(mouse_pos) for rect in {**tools_btns, **action_btns}.values()
    )

    if is_dragging or (dragging_node is not None and mode != "INPUT_WEIGHT"):
        cursor = pygame.SYSTEM_CURSOR_SIZEALL
    elif is_hovering_ui:
        cursor = pygame.SYSTEM_CURSOR_HAND
    elif mode != "INPUT_WEIGHT" and mouse_pos[0] < WORK_WIDTH:
        hovered_node = get_clicked_node(mouse_pos)

        if mode == "ADD_NODE" and hovered_node is None:
            cursor = pygame.SYSTEM_CURSOR_CROSSHAIR
        elif mode == "ADD_EDGE" and hovered_node is not None:
            cursor = pygame.SYSTEM_CURSOR_CROSSHAIR
        elif mode == "DELETE":
            if hovered_node is not None:
                cursor = pygame.SYSTEM_CURSOR_NO
            else:
                is_hovering_edge = False
                for u, v in edges.keys():
                    offset = 12 if (v, u) in edges else 0
                    dx, dy = nodes[v][0] - nodes[u][0], nodes[v][1] - nodes[u][1]
                    length = math.hypot(dx, dy)
                    if length > 0:
                        nx, ny = -dy / length, dx / length
                        p1 = (nodes[u][0] + nx * offset, nodes[u][1] + ny * offset)
                        p2 = (nodes[v][0] + nx * offset, nodes[v][1] + ny * offset)
                        if point_to_segment_dist(mouse_pos, p1, p2) < 10:
                            is_hovering_edge = True
                            break
                if is_hovering_edge:
                    cursor = pygame.SYSTEM_CURSOR_NO
        elif mode in ["SET_SRC", "SET_SINK"] and hovered_node is not None:
            cursor = pygame.SYSTEM_CURSOR_HAND

    try:
        pygame.mouse.set_cursor(cursor)
    except Exception:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # Rysowanie
    screen.fill(BG_COLOR)

    for x in range(0, WORK_WIDTH, 40):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WORK_WIDTH, y))

    for (u, v), w in edges.items():
        offset = 12 if (v, u) in edges else 0
        draw_arrow(screen, EDGE_COLOR, nodes[u], nodes[v], offset)
        dx, dy = nodes[v][0] - nodes[u][0], nodes[v][1] - nodes[u][1]
        length = math.hypot(dx, dy)
        if length > 0:
            nx, ny = -dy / length, dx / length
            mid_x = (nodes[u][0] + nodes[v][0]) / 2 + nx * offset
            mid_y = (nodes[u][1] + nodes[v][1]) / 2 + ny * offset
            if not flow_paths:
                txt_surf = font.render(str(w), True, TEXT_COLOR)
                txt_rect = txt_surf.get_rect(center=(mid_x, mid_y - 15))
                pygame.draw.rect(screen, BG_COLOR, txt_rect.inflate(4, 4))
                screen.blit(txt_surf, txt_rect)

    if mode == "ADD_EDGE" and selected_node is not None and not is_dragging:
        limit_x = min(mouse_pos[0], WORK_WIDTH)
        pygame.draw.aaline(
            screen, EDGE_COLOR, nodes[selected_node], (limit_x, mouse_pos[1])
        )

    for i, pos in enumerate(nodes):
        color = NODE_COLOR
        if i == source_node:
            color = SOURCE_COLOR
        elif i == sink_node:
            color = SINK_COLOR
        if i == selected_node or i == dragging_node:
            pygame.gfxdraw.aacircle(screen, pos[0], pos[1], 22, (255, 255, 255))
            pygame.gfxdraw.filled_circle(screen, pos[0], pos[1], 22, (255, 255, 255))
        pygame.gfxdraw.aacircle(screen, pos[0], pos[1], 20, color)
        pygame.gfxdraw.filled_circle(screen, pos[0], pos[1], 20, color)
        text = str(i)
        if i == source_node:
            text = "IN"
        elif i == sink_node:
            text = "OUT"
        draw_text_centered(
            screen,
            text,
            font,
            (10, 10, 10),
            pygame.Rect(pos[0] - 20, pos[1] - 20, 40, 40),
        )

    if flow_paths:
        offset_multiplier = 8
        flows = {}

        for i, (path, flow) in enumerate(flow_paths):
            color = colors[i % len(colors)]
            current_offset = (i - len(flow_paths) / 2) * offset_multiplier

            for j in range(len(path) - 1):
                u, v = path[j], path[j + 1]
                weight = edges[(u, v)]

                dx, dy = nodes[v][0] - nodes[u][0], nodes[v][1] - nodes[u][1]
                length = math.hypot(dx, dy)
                anim_phase = (current_time / 20.0 / length) % 1.0
                if length > 5.0:
                    nx, ny = -dy / length, dx / length
                    base_offset = 12 if (v, u) in edges else 0

                    num_ants = max(1, int(length / 25))
                    for ant in range(num_ants):
                        ant_phase = (anim_phase + ant / num_ants) % 1.0
                        ant_x = (
                            nodes[u][0]
                            + (dx / length) * ant_phase * (length - 40)
                            + nx * (current_offset * 1.5 + base_offset)
                        )
                        ant_y = (
                            nodes[u][1]
                            + (dy / length) * ant_phase * (length - 40)
                            + ny * (current_offset * 1.5 + base_offset)
                        )
                        pygame.gfxdraw.filled_circle(
                            screen, int(ant_x), int(ant_y), 2, color
                        )

                    mid_x = (nodes[u][0] + nodes[v][0]) / 2 + nx * base_offset
                    mid_y = (nodes[u][1] + nodes[v][1]) / 2 + ny * base_offset
                    label_center = (mid_x, mid_y - 15)
                    if (weight, label_center) not in flows:
                        flows[(weight, label_center)] = []
                    flows[(weight, label_center)].append((str(flow), color))

        gap = 6
        sum_color = (86, 211, 100)  # white
        weight_color = (180, 180, 180)  # white
        plus_color = (200, 200, 200)  # optional color for '+', can use number color too

        for i, (weight, label_center) in enumerate(flows):
            pairs = flows[(weight, label_center)]
            base_x, base_y = label_center

            # Obliczanie sumy wartości przepływu
            values = []
            for flow_str, color in pairs:
                try:
                    values.append(float(flow_str))
                except Exception:
                    values.append(0.0)

            total_value = sum(values)

            # Przygotowanie powierzchni dla sumy (np. "3")
            sum_text = f"{total_value}"
            sum_surface = font.render(sum_text, True, (255, 255, 255))
            sum_width = sum_surface.get_rect().width + 4

            # Przygotowanie powierzchni dla wagi (np. "/4")
            weight_text = f"/ {weight}"
            weight_surface = font.render(weight_text, True, weight_color)
            weight_width = weight_surface.get_rect().width

            # Całkowita szerokość do wyśrodkowania na label_center
            total_width = sum_width + weight_width
            x = base_x - total_width / 2

            # Rysowanie samej sumy
            sum_rect = sum_surface.get_rect(midleft=(x, base_y))
            screen.fill(BG_COLOR, sum_rect.inflate(4, 2))
            screen.blit(sum_surface, sum_rect)

            # Rysowanie wagi (od razu po sumie)
            weight_rect = weight_surface.get_rect(midleft=(x + sum_width, base_y))
            screen.fill(BG_COLOR, weight_rect.inflate(4, 2))
            screen.blit(weight_surface, weight_rect)

        res_text = large_font.render(
            f"Maksymalny przepływ: {max_flow_result}", True, (86, 211, 100)
        )
        screen.blit(res_text, (20, 20))

    hint_str = hints.get(mode, "")
    if hint_str:
        hint_surf = font.render(f"Info: {hint_str}", True, (170, 210, 255))
        screen.blit(hint_surf, (20, HEIGHT - 35))

    pygame.draw.rect(screen, (30, 30, 35), (WORK_WIDTH, 0, PANEL_WIDTH, HEIGHT))
    pygame.draw.line(screen, EDGE_COLOR, (WORK_WIDTH, 0), (WORK_WIDTH, HEIGHT), 2)

    for text, cx, cy in headers:
        txt_surf = large_font.render(text, True, TEXT_COLOR)
        txt_rect = txt_surf.get_rect(center=(cx, cy))
        screen.blit(txt_surf, txt_rect)

    for key, rect in {**tools_btns, **action_btns}.items():
        is_hover = rect.collidepoint(mouse_pos)
        color = get_btn_color(key, mode, is_hover)

        if key in tools_btns and key == mode:
            pygame.draw.rect(
                screen, (200, 210, 220), rect.inflate(4, 4), border_radius=6
            )

        pygame.draw.rect(screen, color, rect, border_radius=5)
        draw_text_centered(screen, labels[key], font, TEXT_COLOR, rect)

    if mode == "INPUT_WEIGHT":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        box_rect = pygame.Rect(WORK_WIDTH // 2 - 200, HEIGHT // 2 - 60, 400, 120)
        pygame.draw.rect(screen, (30, 30, 35), box_rect, border_radius=10)
        pygame.draw.rect(screen, BTN_ACTIVE, box_rect, 2, border_radius=10)
        draw_text_centered(
            screen,
            "Podaj wagę krawędzi (domyślnie 1, Enter by zatwierdzić):",
            font,
            TEXT_COLOR,
            pygame.Rect(box_rect.x, box_rect.y + 20, box_rect.w, 30),
        )
        draw_text_centered(
            screen,
            input_weight_str + "_",
            large_font,
            (255, 255, 255),
            pygame.Rect(box_rect.x, box_rect.y + 60, box_rect.w, 40),
        )

    if current_time - error_msg_time < 2500:
        error_msg_text_width = font.size(error_msg_text)[0] + 20
        err_rect = pygame.Rect(
            WORK_WIDTH // 2 - error_msg_text_width / 2, 70, error_msg_text_width, 40
        )
        pygame.draw.rect(screen, (200, 50, 50), err_rect, border_radius=5)
        draw_text_centered(screen, error_msg_text, font, TEXT_COLOR, err_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
