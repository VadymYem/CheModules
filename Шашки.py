# meta developer: @author_che
# meta name: Шашки та Шахи
# meta version: 2.0.0 # Додано шахи та українізація

import asyncio, html, random
from .. import loader, utils

# Константи для шашок
EMPTY = 0
WHITE_MAN = 1
BLACK_MAN = 2
WHITE_KING = 3
BLACK_KING = 4

# Константи для шахів
CHESS_EMPTY = 0
CHESS_W_KING = 11
CHESS_W_QUEEN = 12
CHESS_W_ROOK = 13
CHESS_W_BISHOP = 14
CHESS_W_KNIGHT = 15
CHESS_W_PAWN = 16
CHESS_B_KING = 21
CHESS_B_QUEEN = 22
CHESS_B_ROOK = 23
CHESS_B_BISHOP = 24
CHESS_B_KNIGHT = 25
CHESS_B_PAWN = 26

PIECE_EMOJIS = {
    EMPTY: ".",
    "light": " ",
    WHITE_MAN: "⚪",
    BLACK_MAN: "⚫",
    WHITE_KING: "🌝",
    BLACK_KING: "🌚",
    'selected': "🔘",
    'move_target': "🟢",
    'capture_target': "🔴",
    # Шахові фігури
    CHESS_W_KING: "♔",
    CHESS_W_QUEEN: "♕",
    CHESS_W_ROOK: "♖",
    CHESS_W_BISHOP: "♗",
    CHESS_W_KNIGHT: "♘",
    CHESS_W_PAWN: "♙",
    CHESS_B_KING: "♚",
    CHESS_B_QUEEN: "♛",
    CHESS_B_ROOK: "♜",
    CHESS_B_BISHOP: "♝",
    CHESS_B_KNIGHT: "♞",
    CHESS_B_PAWN: "♟",
}

class CheckersBoard:
    def __init__(self, mandatory_captures_enabled=True):
        self._board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self._setup_initial_pieces()
        self.current_player = "white"
        self.mandatory_capture_from_pos = None
        self.mandatory_captures_enabled = mandatory_captures_enabled

    def _setup_initial_pieces(self):
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 != 0:
                    if r < 3:
                        self._board[r][c] = BLACK_MAN
                    elif r > 4:
                        self._board[r][c] = WHITE_MAN

    def _is_valid_coord(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_piece_at(self, r, c):
        if not self._is_valid_coord(r, c):
            return None
        return self._board[r][c]

    def _set_piece_at(self, r, c, piece):
        if self._is_valid_coord(r, c):
            self._board[r][c] = piece

    def _get_player_color(self, piece):
        if piece in [WHITE_MAN, WHITE_KING]:
            return "white"
        if piece in [BLACK_MAN, BLACK_KING]:
            return "black"
        return None

    def _get_opponent_color(self, color):
        return "black" if color == "white" else "white"

    def _get_moves_for_piece(self, r, c):
        moves = []
        piece = self.get_piece_at(r, c)
        player_color = self._get_player_color(piece)
        opponent_color = self._get_opponent_color(player_color)

        if piece == EMPTY:
            return []

        all_diagonal_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        if piece in [WHITE_MAN, BLACK_MAN]:
            regular_move_directions = []
            if piece == WHITE_MAN:
                regular_move_directions = [(-1, -1), (-1, 1)]
            elif piece == BLACK_MAN:
                regular_move_directions = [(1, -1), (1, 1)]

            for dr, dc in regular_move_directions:
                new_r, new_c = r + dr, c + dc
                if self._is_valid_coord(new_r, new_c) and self.get_piece_at(new_r, new_c) == EMPTY:
                    moves.append((r, c, new_r, new_c, False))

            for dr, dc in all_diagonal_directions:
                captured_piece_r, captured_piece_c = r + dr, c + dc
                jump_r, jump_c = r + 2 * dr, c + 2 * dc
                
                captured_piece = self.get_piece_at(captured_piece_r, captured_piece_c)

                if (self._is_valid_coord(jump_r, jump_c) and
                    self.get_piece_at(jump_r, jump_c) == EMPTY and
                    self._get_player_color(captured_piece) == opponent_color):
                    
                    moves.append((r, c, jump_r, jump_c, True))

        elif piece in [WHITE_KING, BLACK_KING]:
            for dr, dc in all_diagonal_directions:
                current_r, current_c = r + dr, c + dc
                captured_piece_pos = None

                while self._is_valid_coord(current_r, current_c):
                    piece_on_path = self.get_piece_at(current_r, current_c)
                    piece_on_path_color = self._get_player_color(piece_on_path)

                    if piece_on_path == EMPTY:
                        if captured_piece_pos is None:
                            moves.append((r, c, current_r, current_c, False))
                        else:
                            moves.append((r, c, current_r, current_c, True))
                    elif piece_on_path_color == player_color:
                        break
                    elif piece_on_path_color == opponent_color:
                        if captured_piece_pos is None:
                            captured_piece_pos = (current_r, current_c)
                        else:
                            break
                    
                    current_r += dr
                    current_c += dc
        return moves

    def get_all_possible_moves(self, player_color):
        all_moves = []
        all_captures = []

        if self.mandatory_capture_from_pos:
            r, c = self.mandatory_capture_from_pos
            return [m for m in self._get_moves_for_piece(r, c) if m[4]]
            
        for r in range(8):
            for c in range(8):
                piece = self.get_piece_at(r, c)
                if self._get_player_color(piece) == player_color:
                    moves_for_piece = self._get_moves_for_piece(r, c)
                    for move in moves_for_piece:
                        if move[4]:
                            all_captures.append(move)
                        else:
                            all_moves.append(move)
        
        if self.mandatory_captures_enabled and all_captures: 
            return all_captures
        
        return all_moves + all_captures

    def _execute_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        piece = self.get_piece_at(start_r, start_c)
        self._set_piece_at(end_r, end_c, piece)
        self._set_piece_at(start_r, start_c, EMPTY)

        if is_capture_move:
            dr_diff = end_r - start_r
            dc_diff = end_c - start_c
            
            dr_norm = 0
            if dr_diff != 0:
                dr_norm = dr_diff // abs(dr_diff)
            
            dc_norm = 0
            if dc_diff != 0:
                dc_norm = dc_diff // abs(dc_diff)

            current_r, current_c = start_r + dr_norm, start_c + dc_norm
            while self._is_valid_coord(current_r, current_c) and (current_r, current_c) != (end_r, end_c):
                if self.get_piece_at(current_r, current_c) != EMPTY:
                    self._set_piece_at(current_r, current_c, EMPTY)
                    break
                current_r += dr_norm
                current_c += dc_norm
        
        return is_capture_move

    def make_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        self._execute_move(start_r, start_c, end_r, end_c, is_capture_move)
        
        piece_after_move = self.get_piece_at(end_r, end_c)
        if piece_after_move == WHITE_MAN and end_r == 0:
            self._set_piece_at(end_r, end_c, WHITE_KING)
            piece_after_move = WHITE_KING
        elif piece_after_move == BLACK_MAN and end_r == 7:
            self._set_piece_at(end_r, end_c, BLACK_KING)
            piece_after_move = BLACK_KING

        if is_capture_move:
            self.mandatory_capture_from_pos = (end_r, end_c)
            further_captures = [m for m in self._get_moves_for_piece(end_r, end_c) if m[4]]
            
            if further_captures:
                return True
            else:
                self.mandatory_capture_from_pos = None
                self.switch_turn()
                return False
        else:
            self.mandatory_capture_from_pos = None
            self.switch_turn()
            return False

    def switch_turn(self):
        self.current_player = self._get_opponent_color(self.current_player)

    def is_game_over(self):
        white_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "white")
        black_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "black")

        if white_pieces == 0:
            return "Перемога чорних"
        if black_pieces == 0:
            return "Перемога білих"
        
        if not self.get_all_possible_moves(self.current_player):
            if self.current_player == "white":
                return "Перемога чорних (немає ходів у білих)"
            else:
                return "Перемога білих (немає ходів у чорних)"

        return None

    def to_list_of_emojis(self, selected_pos=None, possible_moves_with_info=None):
        board_emojis = []
        possible_moves_with_info = possible_moves_with_info if possible_moves_with_info else []
        
        possible_move_targets_map = {(move_info[0], move_info[1]): move_info[2] for move_info in possible_moves_with_info}

        for r in range(8):
            row_emojis = []
            for c in range(8):
                piece = self.get_piece_at(r, c)
                current_cell_emoji = PIECE_EMOJIS['light'] if (r + c) % 2 == 0 else PIECE_EMOJIS[piece]
                
                if (r, c) == selected_pos:
                    current_cell_emoji = PIECE_EMOJIS['selected']
                elif (r, c) in possible_move_targets_map:
                    is_capture_move = possible_move_targets_map[(r, c)]
                    current_cell_emoji = PIECE_EMOJIS['capture_target'] if is_capture_move else PIECE_EMOJIS['move_target']
                
                row_emojis.append(current_cell_emoji)
            board_emojis.append(row_emojis)
        return board_emojis
    
    def get_valid_moves_for_selection(self, current_r, current_c):
        piece = self.get_piece_at(current_r, current_c)
        if self._get_player_color(piece) != self.current_player:
            return []

        piece_moves_full_info = self._get_moves_for_piece(current_r, current_c)
        all_game_moves_full_info = self.get_all_possible_moves(self.current_player)
        
        valid_moves_for_selection = []

        if self.mandatory_capture_from_pos:
            if (current_r, current_c) == self.mandatory_capture_from_pos:
                valid_moves_for_selection = [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap]
            else:
                valid_moves_for_selection = []
        else:
            for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info:
                if (s_r, s_c, e_r, e_c, is_cap) in all_game_moves_full_info:
                    valid_moves_for_selection.append((e_r, e_c, is_cap))

        return valid_moves_for_selection

class ChessBoard:
    def __init__(self):
        self._board = [[CHESS_EMPTY for _ in range(8)] for _ in range(8)]
        self._setup_initial_pieces()
        self.current_player = "white"
        self.white_king_moved = False
        self.black_king_moved = False
        self.white_rook_king_moved = False
        self.white_rook_queen_moved = False
        self.black_rook_king_moved = False
        self.black_rook_queen_moved = False
        self.en_passant_target = None

    def _setup_initial_pieces(self):
        # Білі фігури
        self._board[7] = [CHESS_W_ROOK, CHESS_W_KNIGHT, CHESS_W_BISHOP, CHESS_W_QUEEN, 
                         CHESS_W_KING, CHESS_W_BISHOP, CHESS_W_KNIGHT, CHESS_W_ROOK]
        self._board[6] = [CHESS_W_PAWN] * 8
        
        # Чорні фігури
        self._board[0] = [CHESS_B_ROOK, CHESS_B_KNIGHT, CHESS_B_BISHOP, CHESS_B_QUEEN, 
                         CHESS_B_KING, CHESS_B_BISHOP, CHESS_B_KNIGHT, CHESS_B_ROOK]
        self._board[1] = [CHESS_B_PAWN] * 8

    def _is_valid_coord(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_piece_at(self, r, c):
        if not self._is_valid_coord(r, c):
            return None
        return self._board[r][c]

    def _set_piece_at(self, r, c, piece):
        if self._is_valid_coord(r, c):
            self._board[r][c] = piece

    def _get_player_color(self, piece):
        if 11 <= piece <= 16:
            return "white"
        if 21 <= piece <= 26:
            return "black"
        return None

    def _get_opponent_color(self, color):
        return "black" if color == "white" else "white"

    def _is_path_clear(self, start_r, start_c, end_r, end_c):
        """Перевіряє, чи шлях між двома клітинами вільний"""
        dr = 0 if start_r == end_r else (1 if end_r > start_r else -1)
        dc = 0 if start_c == end_c else (1 if end_c > start_c else -1)
        
        r, c = start_r + dr, start_c + dc
        while (r, c) != (end_r, end_c):
            if self.get_piece_at(r, c) != CHESS_EMPTY:
                return False
            r += dr
            c += dc
        return True

    def _get_pawn_moves(self, r, c, piece):
        moves = []
        direction = -1 if piece == CHESS_W_PAWN else 1
        start_row = 6 if piece == CHESS_W_PAWN else 1
        
        # Рух вперед на одну клітинку
        new_r = r + direction
        if self._is_valid_coord(new_r, c) and self.get_piece_at(new_r, c) == CHESS_EMPTY:
            moves.append((r, c, new_r, c, False))
            
            # Рух вперед на дві клітинки з початкової позиції
            if r == start_row and self.get_piece_at(new_r + direction, c) == CHESS_EMPTY:
                moves.append((r, c, new_r + direction, c, False))
        
        # Захоплення по діагоналі
        for dc in [-1, 1]:
            new_r, new_c = r + direction, c + dc
            if self._is_valid_coord(new_r, new_c):
                target_piece = self.get_piece_at(new_r, new_c)
                if target_piece != CHESS_EMPTY and self._get_player_color(target_piece) != self._get_player_color(piece):
                    moves.append((r, c, new_r, new_c, True))
        
        return moves

    def _get_rook_moves(self, r, c):
        moves = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_r, new_c = r + i * dr, c + i * dc
                if not self._is_valid_coord(new_r, new_c):
                    break
                
                target_piece = self.get_piece_at(new_r, new_c)
                if target_piece == CHESS_EMPTY:
                    moves.append((r, c, new_r, new_c, False))
                else:
                    if self._get_player_color(target_piece) != self._get_player_color(self.get_piece_at(r, c)):
                        moves.append((r, c, new_r, new_c, True))
                    break
        
        return moves

    def _get_bishop_moves(self, r, c):
        moves = []
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_r, new_c = r + i * dr, c + i * dc
                if not self._is_valid_coord(new_r, new_c):
                    break
                
                target_piece = self.get_piece_at(new_r, new_c)
                if target_piece == CHESS_EMPTY:
                    moves.append((r, c, new_r, new_c, False))
                else:
                    if self._get_player_color(target_piece) != self._get_player_color(self.get_piece_at(r, c)):
                        moves.append((r, c, new_r, new_c, True))
                    break
        
        return moves

    def _get_knight_moves(self, r, c):
        moves = []
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        
        for dr, dc in knight_moves:
            new_r, new_c = r + dr, c + dc
            if self._is_valid_coord(new_r, new_c):
                target_piece = self.get_piece_at(new_r, new_c)
                if target_piece == CHESS_EMPTY:
                    moves.append((r, c, new_r, new_c, False))
                elif self._get_player_color(target_piece) != self._get_player_color(self.get_piece_at(r, c)):
                    moves.append((r, c, new_r, new_c, True))
        
        return moves

    def _get_queen_moves(self, r, c):
        return self._get_rook_moves(r, c) + self._get_bishop_moves(r, c)

    def _get_king_moves(self, r, c):
        moves = []
        king_moves = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        
        for dr, dc in king_moves:
            new_r, new_c = r + dr, c + dc
            if self._is_valid_coord(new_r, new_c):
                target_piece = self.get_piece_at(new_r, new_c)
                if target_piece == CHESS_EMPTY:
                    moves.append((r, c, new_r, new_c, False))
                elif self._get_player_color(target_piece) != self._get_player_color(self.get_piece_at(r, c)):
                    moves.append((r, c, new_r, new_c, True))
        
        return moves

    def _get_moves_for_piece(self, r, c):
        piece = self.get_piece_at(r, c)
        if piece == CHESS_EMPTY:
            return []

        piece_type = piece % 10
        
        if piece_type == 6:  # Пішак
            return self._get_pawn_moves(r, c, piece)
        elif piece_type == 3:  # Тура
            return self._get_rook_moves(r, c)
        elif piece_type == 4:  # Слон
            return self._get_bishop_moves(r, c)
        elif piece_type == 5:  # Кінь
            return self._get_knight_moves(r, c)
        elif piece_type == 2:  # Ферзь
            return self._get_queen_moves(r, c)
        elif piece_type == 1:  # Король
            return self._get_king_moves(r, c)
        
        return []

    def get_all_possible_moves(self, player_color):
        all_moves = []
        
        for r in range(8):
            for c in range(8):
                piece = self.get_piece_at(r, c)
                if self._get_player_color(piece) == player_color:
                    moves_for_piece = self._get_moves_for_piece(r, c)
                    all_moves.extend(moves_for_piece)
        
        return all_moves

    def make_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        piece = self.get_piece_at(start_r, start_c)
        
        # Оновлення флагів рокіровки
        if piece == CHESS_W_KING:
            self.white_king_moved = True
        elif piece == CHESS_B_KING:
            self.black_king_moved = True
        elif piece == CHESS_W_ROOK:
            if start_c == 0:
                self.white_rook_queen_moved = True
            elif start_c == 7:
                self.white_rook_king_moved = True
        elif piece == CHESS_B_ROOK:
            if start_c == 0:
                self.black_rook_queen_moved = True
            elif start_c == 7:
                self.black_rook_king_moved = True

        # Виконання ходу
        self._set_piece_at(end_r, end_c, piece)
        self._set_piece_at(start_r, start_c, CHESS_EMPTY)
        
        # Перетворення пішака
        if piece == CHESS_W_PAWN and end_r == 0:
            self._set_piece_at(end_r, end_c, CHESS_W_QUEEN)
        elif piece == CHESS_B_PAWN and end_r == 7:
            self._set_piece_at(end_r, end_c, CHESS_B_QUEEN)

        self.switch_turn()
        return False

    def switch_turn(self):
        self.current_player = self._get_opponent_color(self.current_player)

    def is_game_over(self):
        # Спрощена перевірка кінця гри
        if not self.get_all_possible_moves(self.current_player):
            if self.current_player == "white":
                return "Перемога чорних (немає ходів у білих)"
            else:
                return "Перемога білих (немає ходів у чорних)"
        return None

    def to_list_of_emojis(self, selected_pos=None, possible_moves_with_info=None):
        board_emojis = []
        possible_moves_with_info = possible_moves_with_info if possible_moves_with_info else []
        
        possible_move_targets_map = {(move_info[0], move_info[1]): move_info[2] for move_info in possible_moves_with_info}

        for r in range(8):
            row_emojis = []
            for c in range(8):
                piece = self.get_piece_at(r, c)
                current_cell_emoji = PIECE_EMOJIS['light'] if (r + c) % 2 == 0 else PIECE_EMOJIS.get(piece, ".")
                
                if (r, c) == selected_pos:
                    current_cell_emoji = PIECE_EMOJIS['selected']
                elif (r, c) in possible_move_targets_map:
                    is_capture_move = possible_move_targets_map[(r, c)]
                    current_cell_emoji = PIECE_EMOJIS['capture_target'] if is_capture_move else PIECE_EMOJIS['move_target']
                
                row_emojis.append(current_cell_emoji)
            board_emojis.append(row_emojis)
        return board_emojis

    def get_valid_moves_for_selection(self, current_r, current_c):
        piece = self.get_piece_at(current_r, current_c)
        if self._get_player_color(piece) != self.current_player:
            return []

        moves = self._get_moves_for_piece(current_r, current_c)
        return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in moves]


@loader.tds
class CheckersChess(loader.Module):
    """Шашки та шахи для гри вдвох."""
    strings = {
        "name": "CheckersChess"
    }

    async def client_ready(self):
        await self.purgeSelf()

    async def purgeSelf(self):
        """Скидає всі змінні стану гри."""
        self._board_obj = None
        self._game_message = None
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.colorName = "випадково"
        self.host_color = None
        self.game_running = False
        self.game_reason_ended = None
        self.players_ids = []
        self.host_id = None
        self.opponent_id = None
        self.opponent_name = None
        self.player_white_id = None
        self.player_black_id = None
        self._game_board_call = None
        self.mandatory_captures_enabled = self.db.get("checkers_module", "mandatory_captures_enabled", True)
        self.game_type = None  # "checkers" або "chess"

    async def settings_menu(self, call):
        if call.from_user.id != self.host_id:
            await call.answer("Тільки власник бота може змінювати налаштування цієї партії!")
            return  
        
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "білий"
        elif self.host_color == "black":
            current_host_color_display = "чорний"
        else:
            current_host_color_display = "випадково"

        opponent_name_display_for_settings = "будь-хто бажаючий"
        invite_text_prefix_for_settings = "Вас запрошують зіграти партію, приймете?"
        if self.opponent_id:
            try:
                opponent_entity = await self.client.get_entity(self.opponent_id)
                opponent_name_display_for_settings = html.escape(opponent_entity.first_name)
            except Exception:
                pass
            invite_text_prefix_for_settings = f"<a href='tg://user?id={self.opponent_id}'>{opponent_name_display_for_settings}</a>, вас запросили зіграти партію, приймете?"

        game_name = "шашки" if self.game_type == "checkers" else "шахи"
        settings_text = f"{invite_text_prefix_for_settings} в {game_name}\n-- --\n"
        settings_text += f"Поточні налаштування:\n"
        settings_text += f"| - > • Хост грає за {current_host_color_display} колір\n"
        
        if self.game_type == "checkers":
            settings_text += f"| - > • Обов'язкові взяття: {'Увімкнені' if self.mandatory_captures_enabled else 'Вимкнені'}"

        buttons = [
            [{"text":f"Колір (хоста): {current_host_color_display}","callback":self.set_color}]
        ]
        
        if self.game_type == "checkers":
            buttons.append([
                {"text":f"Обов'язкові взяття: {'Увімк' if self.mandatory_captures_enabled else 'Вимк'}","callback":self.toggle_mandatory_captures}
            ])
        
        buttons.append([
            {"text":"Повернутися","callback":self.back_to_invite}
        ])

        await call.edit(
            text=settings_text,
            reply_markup=buttons
        )

    async def toggle_mandatory_captures(self, call):
        if call.from_user.id != self.host_id:
            await call.answer("Тільки власник бота може змінювати налаштування цієї партії!")
            return
        self.mandatory_captures_enabled = not self.mandatory_captures_enabled
        self.db.set("checkers_module", "mandatory_captures_enabled", self.mandatory_captures_enabled)
        await self.settings_menu(call)

    async def back_to_invite(self, call):
        if call.from_user.id != self.host_id:
            await call.answer("Це не для вас!")
            return
        
        opponent_name_display = "будь-хто бажаючий"
        invite_text_prefix = "Вас запрошують зіграти партію, приймете?"

        if self.opponent_id:
            try:
                opponent_entity = await self.client.get_entity(self.opponent_id)
                opponent_name_display = html.escape(opponent_entity.first_name)
            except Exception:
                pass
            invite_text_prefix = f"<a href='tg://user?id={self.opponent_id}'>{opponent_name_display}</a>, вас запросили зіграти партію, приймете?"

        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "білий"
        elif self.host_color == "black":
            current_host_color_display = "чорний"
        else:
            current_host_color_display = "випадково"

        game_name = "шашки" if self.game_type == "checkers" else "шахи"
        settings_text = f"{invite_text_prefix} в {game_name}\n-- --\n"
        settings_text += f"Поточні налаштування:\n"
        settings_text += f"| - > • Хост грає за {current_host_color_display} колір\n"
        
        if self.game_type == "checkers":
            settings_text += f"| - > • Обов'язкові взяття: {'Увімкнені' if self.mandatory_captures_enabled else 'Вимкнені'}"

        await call.edit(
            text=settings_text,
            reply_markup = [
                [
                    {"text": "Приймаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Ні", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "Змінити налаштування", "callback": self.settings_menu}
                ]
            ]
        )

    async def set_color(self, call):
        if call.from_user.id != self.host_id:
            await call.answer("Тільки власник бота може змінювати налаштування кольору!")
            return
        
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "білий"
        elif self.host_color == "black":
            current_host_color_display = "чорний"
        else:
            current_host_color_display = "випадково"

        await call.edit(
            text=f"• Налаштування цієї партії.\n"
                 f"| - > Хост грає за: {current_host_color_display} колір.\nВиберіть колір його фігур",
            reply_markup=[
                [
                    {"text":"Білі","callback":self.handle_color_choice,"args":("white","білий",)},
                    {"text":"Чорні","callback":self.handle_color_choice,"args":("black","чорний",)}
                ],
                [
                    {"text":"Випадково", "callback":self.handle_color_choice,"args":(None,"випадково")}
                ],
                [
                    {"text":"Назад до налаштувань", "callback":self.settings_menu}
                ]
            ]
        )

    async def handle_color_choice(self, call, color, txt):
        if call.from_user.id != self.host_id:
            await call.answer("Тільки власник бота може вибирати колір!")
            return
        self.colorName = txt
        self.host_color = color
        await self.set_color(call)

    @loader.command() 
    async def шашки(self, message):
        """[reply/username/id] запропонувати людині зіграти партію в чаті. Без аргументів - будь-хто бажаючий."""
        if self._board_obj:
            await message.edit("Партія вже десь запущена. Завершіть або скиньте її з <code>.стопгра</code>")
            return
        await self.purgeSelf()
        self.game_type = "checkers"
        return await self._start_game(message, "шашки")

    @loader.command() 
    async def шахи(self, message):
        """[reply/username/id] запропонувати людині зіграти партію в шахи. Без аргументів - будь-хто бажаючий."""
        if self._board_obj:
            await message.edit("Партія вже десь запущена. Завершіть або скиньте її з <code>.стопгра</code>")
            return
        await self.purgeSelf()
        self.game_type = "chess"
        return await self._start_game(message, "шахи")

    async def _start_game(self, message, game_name):
        self._game_message = message
        self._game_chat_id = message.chat_id
        self.host_id = message.sender_id

        opponent_found = False
        invite_text_prefix = ""

        if message.is_reply:
            r = await message.get_reply_message()
            opponent = r.sender
            self.opponent_id = opponent.id
            self.opponent_name = html.escape(opponent.first_name)
            opponent_found = True
        else:
            args = utils.get_args(message)
            if len(args) > 0:
                opponent_str = args[0]
                try:
                    if opponent_str.isdigit():
                        self.opponent_id = int(opponent_str)
                        opponent = await self.client.get_entity(self.opponent_id)
                        self.opponent_name = html.escape(opponent.first_name)
                    else:
                        opponent = await self.client.get_entity(opponent_str)
                        self.opponent_name = html.escape(opponent.first_name)
                        self.opponent_id = opponent.id
                    opponent_found = True
                except Exception:
                    await message.edit("Я не знаходжу такого користувача")
                    return
        
        if opponent_found:
            if self.opponent_id == self._game_message.sender_id:
                await message.edit(f"Одиночні {game_name}? Вибачте, ні.")
                return
            self.players_ids = [self.opponent_id, self._game_message.sender_id]
            invite_text_prefix = f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас запросили зіграти партію в {game_name}, приймете?"
        else:
            self.opponent_id = None
            self.opponent_name = "будь-хто бажаючий"
            invite_text_prefix = f"Вас запрошують зіграти партію в {game_name}, приймете?"
        
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "білий"
        elif self.host_color == "black":
            current_host_color_display = "чорний"
        else:
            current_host_color_display = "випадково"

        settings_text = f"{invite_text_prefix}\n-- --\n"
        settings_text += f"Поточні налаштування:\n"
        settings_text += f"| - > • Хост грає за {current_host_color_display} колір\n"
        
        if self.game_type == "checkers":
            settings_text += f"| - > • Обов'язкові взяття: {'Увімкнені' if self.mandatory_captures_enabled else 'Вимкнені'}"

        await self.inline.form(
            message = message,
            text = settings_text,
            reply_markup = [
                [
                    {"text": "Приймаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Ні", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "Змінити налаштування", "callback": self.settings_menu}
                ]
            ], 
            disable_security = True,
            on_unload=self.outdated_game
        )

    @loader.command() 
    async def стопгра(self, message):
        """Дострокове завершення партії (для хоста або будь-якого гравця)"""
        if not self.game_running and self.opponent_id is None:
            if message.from_user.id != self.host_id:
                await message.edit("Ви не організатор цієї партії і не можете її зупинити до початку.")
                return
        elif message.from_user.id != self.host_id and message.from_user.id not in self.players_ids:
            await message.edit("Ви не гравець цієї партії і не її організатор.")
            return

        if self._game_board_call:
            try:
                await self._game_board_call.edit(text="Партію було зупинено.")
            except Exception:
                pass
        elif self._game_message:
            try:
                await self._game_message.edit(text="Партію було зупинено.")
            except Exception:
                pass
        
        await self.purgeSelf()
        await message.edit("Дані очищено.")

    async def accept_game(self, call, data):
        if call.from_user.id == self.host_id:
            if self.opponent_id is None and data == 'n':
                await call.edit(text="Партію скасовано.")
                await self.purgeSelf()
                return
            await call.answer("Дай людині відповісти!")
            return
        
        if data == 'y':
            if self.opponent_id is None:
                self.opponent_id = call.from_user.id
                try:
                    opponent_entity = await self.client.get_entity(self.opponent_id)
                    self.opponent_name = html.escape(opponent_entity.first_name)
                except Exception:
                    self.opponent_name = "Невідомий гравець"
                await call.answer(f"Ви приєдналися до гри як {self.opponent_name}!")
                self.players_ids = [self.opponent_id, self.host_id]
            elif call.from_user.id != self.opponent_id:
                await call.answer("Не тобі пропонують гру!")
                return
            
            if self.game_type == "checkers":
                self._board_obj = CheckersBoard(mandatory_captures_enabled=self.mandatory_captures_enabled) 
            else:
                self._board_obj = ChessBoard()
            
            if not self.host_color:
                await call.edit(text="Вибираю сторони...")
                await asyncio.sleep(0.5)
                self.host_color = self.ranColor()
            
            if self.host_color == "white":
                self.player_white_id = self.host_id
                self.player_black_id = self.opponent_id
            else:
                self.player_white_id = self.opponent_id
                self.player_black_id = self.host_id

            text = await self.get_game_status_text()
            await call.edit(text="Завантаження дошки...")
            await asyncio.sleep(0.5)
            
            self.game_running = True
            self._game_board_call = call
            
            await call.edit(text="Для кращого розрізнення фігур увімкніть світлу тему!")
            await asyncio.sleep(2.5)
            await self.render_board(text, call)
        else:
            if self.opponent_id is None:
                await call.answer("Тільки організатор може скасувати гру, до якої може приєднатися будь-хто бажаючий.")
                return
            elif call.from_user.id != self.opponent_id:
                await call.answer("Не тобі пропонують гру!")
                return
            
            await call.edit(text="Відхилено.")
            await self.purgeSelf()

    async def render_board(self, text, call):
        if not self._board_obj:
            await call.edit(text="Помилка: Дошка гри не ініціалізована. Гру завершено.")
            await self.purgeSelf()
            return

        board_emojis = self._board_obj.to_list_of_emojis(self._selected_piece_pos, self._possible_moves_for_selected)
        
        btns = []
        for r in range(8):
            row_btns = []
            for c in range(8):
                row_btns.append({"text": board_emojis[r][c], "callback": self.handle_click, "args":(r, c,)})
            btns.append(row_btns)

        btns.append([{"text": "Здатися", "callback": self.surrender_game}])

        await call.edit(
            text = text,
            reply_markup = btns,
            disable_security = True
        )
    
    async def surrender_game(self, call):
        user_id = call.from_user.id
        
        if user_id not in [self.player_white_id, self.player_black_id]:
            await call.answer("Ви не гравець цієї партії і не можете здатися. Використовуйте .стопгра для примусової зупинки.")
            return

        surrendering_player_name = "Невідомий гравець"
        try:
            surrendering_player_entity = await self.client.get_entity(user_id)
            surrendering_player_name = html.escape(surrendering_player_entity.first_name)
        except Exception:
            pass

        winner_id = None
        winner_color_text = ""
        if user_id == self.player_white_id:
            winner_id = self.player_black_id
            winner_color_text = "чорних"
        elif user_id == self.player_black_id:
            winner_id = self.player_white_id
            winner_color_text = "білих"
        
        winner_name = "Опонент"
        if winner_id:
            try:
                winner_entity = await self.client.get_entity(winner_id)
                winner_name = html.escape(winner_entity.first_name)
            except Exception:
                pass

        game_name = "шашки" if self.game_type == "checkers" else "шахи"
        surrender_message = (
            f"Партію в {game_name} завершено: <a href='tg://user?id={user_id}'>{surrendering_player_name}</a> здався(лась).\n"
            f"Переміг(ла) <a href='tg://user?id={winner_id}'>{winner_name}</a> ({winner_color_text})!"
        )

        self.game_running = False
        self.game_reason_ended = surrender_message
        
        await call.edit(surrender_message)
        await self.purgeSelf()
        
    async def handle_click(self, call, r, c):
        if not self._board_obj or not self.game_running:
            await call.answer("Гра не активна або завершена. Почніть нову гру.")
            if self._board_obj:
                await self.purgeSelf()
            return

        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            if self.game_running:
                self.game_running = False
                self.game_reason_ended = game_over_status
                await self.render_board(await self.get_game_status_text(), call)
                await self.purgeSelf()
            await call.answer(f"Партію закінчено: {game_over_status}. Для нової гри використовуйте команду")
            return
        
        if call.from_user.id not in self.players_ids: 
            await call.answer("Партія не ваша!")
            return
        
        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        if call.from_user.id != current_player_id:
            await call.answer("Зараз хід опонента!")
            return

        piece_at_click = self._board_obj.get_piece_at(r, c)
        player_color_at_click = self._board_obj._get_player_color(piece_at_click)

        if self._selected_piece_pos is None:
            if player_color_at_click == self._board_obj.current_player:
                # Перевірка на обов'язковий мульти-захват для шашок
                if (self.game_type == "checkers" and 
                    hasattr(self._board_obj, 'mandatory_capture_from_pos') and 
                    self._board_obj.mandatory_capture_from_pos and 
                    self._board_obj.mandatory_capture_from_pos != (r, c)):
                    await call.answer("Ви повинні продовжити захват з попередньої позиції!")
                    return

                possible_moves_with_info = self._board_obj.get_valid_moves_for_selection(r, c)
                
                if possible_moves_with_info:
                    self._selected_piece_pos = (r, c)
                    self._possible_moves_for_selected = possible_moves_with_info
                    await call.answer("Фігуру вибрано. Виберіть куди ходити.")
                    await self.render_board(await self.get_game_status_text(), call)
                else:
                    await call.answer("Для цієї фігури немає доступних ходів!")
            else:
                await call.answer("Тут немає вашої фігури або це світла клітинка!")
        else:
            start_r, start_c = self._selected_piece_pos
            
            if (r, c) == (start_r, start_c):
                self._selected_piece_pos = None
                self._possible_moves_for_selected = []
                await call.answer("Вибір скасовано.")
                await self.render_board(await self.get_game_status_text(), call)
                return

            target_move_info = None
            for move_info in self._possible_moves_for_selected:
                if (move_info[0], move_info[1]) == (r, c):
                    target_move_info = move_info
                    break

            if target_move_info:
                end_r, end_c, is_capture_move = target_move_info
                made_capture_and_can_jump_again = self._board_obj.make_move(start_r, start_c, end_r, end_c, is_capture_move)
                
                if made_capture_and_can_jump_again and self.game_type == "checkers":
                    self._selected_piece_pos = (end_r, end_c)
                    self._possible_moves_for_selected = self._board_obj.get_valid_moves_for_selection(end_r, end_c)
                    await call.answer("Захват! Зробіть наступний захват.")
                else:
                    self._selected_piece_pos = None
                    self._possible_moves_for_selected = []
                    await call.answer("Хід зроблено.")
                
                game_over_status_after_move = self._board_obj.is_game_over()
                if game_over_status_after_move:
                    self.game_running = False
                    self.game_reason_ended = game_over_status_after_move
                    await call.answer(f"Партію закінчено: {game_over_status_after_move}")
                    await self.render_board(await self.get_game_status_text(), call)
                    await self.purgeSelf()
                    return
                
                await self.render_board(await self.get_game_status_text(), call)
            else:
                if player_color_at_click == self._board_obj.current_player:
                    # Перевірка на обов'язковий мульти-захват для шашок
                    if (self.game_type == "checkers" and 
                        hasattr(self._board_obj, 'mandatory_capture_from_pos') and 
                        self._board_obj.mandatory_capture_from_pos and 
                        self._board_obj.mandatory_capture_from_pos != (r, c)):
                        await call.answer("Ви повинні продовжити захват з попередньої позиції!")
                        return
                    
                    possible_moves_with_info = self._board_obj.get_valid_moves_for_selection(r, c)
                    
                    if possible_moves_with_info:
                        self._selected_piece_pos = (r, c)
                        self._possible_moves_for_selected = possible_moves_with_info
                        await call.answer("Вибрано іншу фігуру.")
                        await self.render_board(await self.get_game_status_text(), call)
                    else:
                        await call.answer("Для цієї фігури немає доступних ходів!")
                else:
                    await call.answer("Неправильний хід або ціль не є вашою фігурою!")

    async def get_game_status_text(self):
        if not self._board_obj:
            return "Гра не активна або завершена."

        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            if self.game_reason_ended:
                return self.game_reason_ended
            
            winner_name = ""
            game_name = "шашки" if self.game_type == "checkers" else "шахи"
            if "Перемога білих" in game_over_status:
                try:
                    winner_name = html.escape((await self.client.get_entity(self.player_white_id)).first_name)
                    return f"Партію в {game_name} закінчено: {game_over_status}\n\nПереміг(ла) <a href='tg://user?id={self.player_white_id}'>{winner_name}</a> (білі)!"
                except Exception:
                    return f"Партію в {game_name} закінчено: {game_over_status}\n\nПеремогли Білі!"
            elif "Перемога чорних" in game_over_status:
                try:
                    winner_name = html.escape((await self.client.get_entity(self.player_black_id)).first_name)
                    return f"Партію в {game_name} закінчено: {game_over_status}\n\nПереміг(ла) <a href='tg://user?id={self.player_black_id}'>{winner_name}</a> (чорні)!"
                except Exception:
                    return f"Партію в {game_name} закінчено: {game_over_status}\n\nПеремогли Чорні!"
            return f"Партію в {game_name} закінчено: {game_over_status}"

        white_player_name = "Білі"
        black_player_name = "Чорні"
        try:
            white_player_entity = await self.client.get_entity(self.player_white_id)
            white_player_name = html.escape(white_player_entity.first_name)
        except Exception:
            pass
        
        try:
            black_player_entity = await self.client.get_entity(self.player_black_id)
            black_player_name = html.escape(black_player_entity.first_name)
        except Exception:
            pass

        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        current_player_name = "Невідомий гравець"
        try:
            current_player_name_entity = await self.client.get_entity(current_player_id)
            current_player_name = html.escape(current_player_name_entity.first_name)
        except Exception:
            pass
        
        game_name = "Шашки" if self.game_type == "checkers" else "Шахи"
        status_text = f"{game_name}\n♔ Білі - <a href='tg://user?id={self.player_white_id}'>{white_player_name}</a>\n♚ Чорні - <a href='tg://user?id={self.player_black_id}'>{black_player_name}</a>\n\n"
        
        if self._board_obj.current_player == "white":
            status_text += f"Хід білих (<a href='tg://user?id={current_player_id}'>{current_player_name}</a>)"
        else:
            status_text += f"Хід чорних (<a href='tg://user?id={current_player_id}'>{current_player_name}</a>)"
        
        if self.game_type == "checkers":
            status_text += f"\nОбов'язкові взяття: {'Увімкнені' if self.mandatory_captures_enabled else 'Вимкнені'}"

            if hasattr(self._board_obj, 'mandatory_capture_from_pos') and self._board_obj.mandatory_capture_from_pos:
                status_text += "\nОбов'язковий захват!"

        return status_text

    async def outdated_game(self):
        if self.game_running or self._board_obj:
            if self._game_board_call:
                try:
                    await self._game_board_call.edit(text="Партія застаріла через відсутність активності.")
                except Exception:
                    pass
            elif self._game_message:
                try:
                    await self._game_message.edit(text="Партія застаріла через відсутність активності.")
                except Exception:
                    pass
            await self.purgeSelf()

    def ranColor(self):
        return "white" if random.randint(1,2) == 1 else "black"