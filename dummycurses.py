"""Super-minimal 'curses'

Provides the functions _pyrepl needs, hardcoding values to `xterm-256color`
(which "new" terminal emulators are likely to support).
If your $TERM is different, try substituting your own `infocmp` output.

Use this instead of _pyrepl._minimal_curses.

See `man terminfo` for docs on the format.
"""
import re

class error(Exception):
    pass

def setupterm(termstr, fd):
    pass

def tigetstr(cap, caps=None):
    if isinstance(cap, bytes):
        cap = cap.encode("ascii")
    if caps is None:
        caps = _TERMINFO
    return caps.get(cap, None)

def tparm(s, *params, variables={}):
    # `variables` persist between calls, hence the mutable default.
    pos = 0
    stack = []
    push = stack.append
    pop = stack.pop
    parts = []
    output = parts.append
    if_stack = []
    active = True
    def get_param(i):
        try:
            return params[i]
        except IndexError:
            return 0
    while True:
        percent_pos = s.find(b'%', pos)
        if percent_pos == -1:
            if active:
                output(s[pos:])
            break
        if active:
            output(s[pos:percent_pos])
        pos = percent_pos + 1
        control = s[pos:pos+1]
        #print(s[:pos], stack, s[pos:], if_stack, b''.join(parts))
        if control in b'?te;':
            match control:
                case b'?':
                    if_stack.append('cond')
                case b't':
                    if active:
                        val = bool(pop())
                        if val:
                            if_stack[-1] = 'then'
                        else:
                            if_stack[-1] = 'wait'
                case b'e':
                    if if_stack[-1] == 'wait':
                        if_stack[-1] = 'cond'
                    if if_stack[-1] == 'then':
                        if_stack[-1] = 'skip'
                case b';':
                    if_stack.pop()
            pos += 1
            active = all(e in {'cond', 'then'} for e in if_stack)
            continue
        if not active:
            continue
        match control:
            case b'%': output(b'%')
            case b'c':
                char = pop()
                if char == 0:
                    char = 0x80
                char &= 0xff
                if char == 0:
                    # ncurses outputs a zero byte, ending the string
                    break
                output(bytes([char]))
            case b's':
                val = pop()
                if val:
                    output(str(pop()).encode('ascii'))
            case b'l': push(len(str(pop())))
            case b'+': b = pop(); a = pop(); push(a + b)
            case b'-': b = pop(); a = pop(); push(a - b)
            case b'*': b = pop(); a = pop(); push(a * b)
            case b'/': b = pop(); a = pop(); push(int(a / b))
            case b'm': b = pop(); a = pop(); push(a - (int(a / b) * b))
            case b'&': b = pop(); a = pop(); push(a & b)
            case b'|': b = pop(); a = pop(); push(a | b)
            case b'^': b = pop(); a = pop(); push(a ^ b)
            case b'=': b = pop(); a = pop(); push(a == b)
            case b'>': b = pop(); a = pop(); push(a > b)
            case b'<': b = pop(); a = pop(); push(a < b)
            case b'A': b = pop(); a = pop(); push(int(bool(a and b)))
            case b'O': b = pop(); a = pop(); push(int(bool(a or b)))
            case b'!': push(int(not pop()))
            case b'~': push(~pop())
            case b'p':
                pos += 1
                push(int(get_param(int(s[pos:pos+1]) - 1)))
            case b'P':
                pos += 1
                name = s[pos:pos+1]
                variables[name] = pop()
            case b'g':
                pos += 1
                name = s[pos:pos+1]
                push(variables.get(name, 0))
            case b"'":
                push(ord(s[pos+1:pos+2]))
                pos += 2
            case b'{':
                end = s.index(b'}', pos)
                push(int(s[pos+1:end]))
                pos = end
            case b'i':
                params = (get_param(0) + 1, get_param(1) + 1, *params[2:])
                push(params[0])
                push(params[1])
            case _:
                match = re.compile(b'[doxXs]').search(s, pos)
                if match:
                    end = match.start()
                    fmt = s[pos-1:end+1]
                    if s[pos:pos+1] == ':':
                        fmt = '%' + fmt[2:]
                    val = pop()
                    if val < 0 and fmt[-1] in b'xXo':
                        val = val & 0xFFFFFFFF
                    output(fmt % val)
                    pos = end
        pos += 1
    return b''.join(parts)

def _get_terminfo(source, exclude=()):
    lines = [l for l in source.splitlines() if not l.startswith('#')]
    source = ' '.join(lines).strip(' ,')
    fields = re.split(r',( |$)', source)
    field_iter = iter(fields)
    names = next(field_iter)

    result = {}
    for field in field_iter:
        try:
            name, sep, value = field.strip().partition('=')
            if name in exclude:
                continue
            if sep:
                value = value.replace(r'^?', '\x7f')
                value = re.sub(r'(?<!\\)\^(.)', lambda m: chr(ord(m[1]) & 0x1f), value)
                assert '^' not in value.replace(r'\^', ''), value
                value = value.replace(r'\E', '\x1b')
                value = value.replace(r'\e', '\x1b')
                value = value.replace(r'\r', '\r')
                value = value.replace(r'\n', '\n')
                value = value.replace(r'\t', '\t')
                value = value.replace(r'\b', '\b')
                value = value.replace(r'\f', '\f')
                value = value.replace(r'\s', ' ')
                value = re.sub(r'\\([\d]{3})', lambda m: chr(int(m[1], 8)), value)
                value = value.replace(r'\^', '^')
                value = value.replace(r'\,', ',')
                value = value.replace(r'\:', ':')
                value = value.replace(r'\0', '\200')
                assert '\\' not in value.replace(r'\\', ''), value
                value = value.replace(r'\\', '\\')
                #assert '$<' not in value, value  # `$<..>` means delay
                #assert '%?' not in value, value  # %? is a if-else operator
                result[name] = value.encode('latin1')
        except Exception as e:
            e.add_note(field)
            raise
    return result

# terminfo data obtained with:  infocmp xterm-256color
# (OK to use; see 'COPYRIGHTS AND OTHER DELUSIONS' in terminfo.src in
#  ncurses for details.)
# TODO: Implement features for missing capabilities
_TERM = 'xterm-256color'
_TERMINFO = _get_terminfo(
    exclude={},
    source=r"""
#	Reconstructed via infocmp from file: /usr/share/terminfo/x/xterm-256color
xterm-256color|xterm with 256 colors,
        am, bce, ccc, km, mc5i, mir, msgr, npc, xenl,
        colors#0x100, cols#80, it#8, lines#24, pairs#0x10000,
        acsc=``aaffggiijjkkllmmnnooppqqrrssttuuvvwwxxyyzz{{||}}~~,
        bel=^G, blink=\E[5m, bold=\E[1m, cbt=\E[Z, civis=\E[?25l,
        clear=\E[H\E[2J, cnorm=\E[?12l\E[?25h, cr=\r,
        csr=\E[%i%p1%d;%p2%dr, cub=\E[%p1%dD, cub1=^H,
        cud=\E[%p1%dB, cud1=\n, cuf=\E[%p1%dC, cuf1=\E[C,
        cup=\E[%i%p1%d;%p2%dH, cuu=\E[%p1%dA, cuu1=\E[A,
        cvvis=\E[?12;25h, dch=\E[%p1%dP, dch1=\E[P, dim=\E[2m,
        dl=\E[%p1%dM, dl1=\E[M, ech=\E[%p1%dX, ed=\E[J, el=\E[K,
        el1=\E[1K, flash=\E[?5h$<100/>\E[?5l, home=\E[H,
        hpa=\E[%i%p1%dG, ht=^I, hts=\EH, ich=\E[%p1%d@,
        il=\E[%p1%dL, il1=\E[L, ind=\n, indn=\E[%p1%dS,
        initc=\E]4;%p1%d;rgb:%p2%{255}%*%{1000}%/%2.2X/%p3%{255}%*%{1000}%/%2.2X/%p4%{255}%*%{1000}%/%2.2X\E\\,
        invis=\E[8m, is2=\E[!p\E[?3;4l\E[4l\E>, kDC=\E[3;2~,
        kEND=\E[1;2F, kHOM=\E[1;2H, kIC=\E[2;2~, kLFT=\E[1;2D,
        kNXT=\E[6;2~, kPRV=\E[5;2~, kRIT=\E[1;2C, ka1=\EOw,
        ka3=\EOy, kb2=\EOu, kbeg=\EOE, kbs=^?, kc1=\EOq, kc3=\EOs,
        kcbt=\E[Z, kcub1=\EOD, kcud1=\EOB, kcuf1=\EOC, kcuu1=\EOA,
        kdch1=\E[3~, kend=\EOF, kent=\EOM, kf1=\EOP, kf10=\E[21~,
        kf11=\E[23~, kf12=\E[24~, kf13=\E[1;2P, kf14=\E[1;2Q,
        kf15=\E[1;2R, kf16=\E[1;2S, kf17=\E[15;2~, kf18=\E[17;2~,
        kf19=\E[18;2~, kf2=\EOQ, kf20=\E[19;2~, kf21=\E[20;2~,
        kf22=\E[21;2~, kf23=\E[23;2~, kf24=\E[24;2~,
        kf25=\E[1;5P, kf26=\E[1;5Q, kf27=\E[1;5R, kf28=\E[1;5S,
        kf29=\E[15;5~, kf3=\EOR, kf30=\E[17;5~, kf31=\E[18;5~,
        kf32=\E[19;5~, kf33=\E[20;5~, kf34=\E[21;5~,
        kf35=\E[23;5~, kf36=\E[24;5~, kf37=\E[1;6P, kf38=\E[1;6Q,
        kf39=\E[1;6R, kf4=\EOS, kf40=\E[1;6S, kf41=\E[15;6~,
        kf42=\E[17;6~, kf43=\E[18;6~, kf44=\E[19;6~,
        kf45=\E[20;6~, kf46=\E[21;6~, kf47=\E[23;6~,
        kf48=\E[24;6~, kf49=\E[1;3P, kf5=\E[15~, kf50=\E[1;3Q,
        kf51=\E[1;3R, kf52=\E[1;3S, kf53=\E[15;3~, kf54=\E[17;3~,
        kf55=\E[18;3~, kf56=\E[19;3~, kf57=\E[20;3~,
        kf58=\E[21;3~, kf59=\E[23;3~, kf6=\E[17~, kf60=\E[24;3~,
        kf61=\E[1;4P, kf62=\E[1;4Q, kf63=\E[1;4R, kf7=\E[18~,
        kf8=\E[19~, kf9=\E[20~, khome=\EOH, kich1=\E[2~,
        kind=\E[1;2B, kmous=\E[<, knp=\E[6~, kpp=\E[5~,
        kri=\E[1;2A, mc0=\E[i, mc4=\E[4i, mc5=\E[5i, meml=\El,
        memu=\Em, mgc=\E[?69l, nel=\EE, oc=\E]104\007,
        op=\E[39;49m, rc=\E8, rep=%p1%c\E[%p2%{1}%-%db,
        rev=\E[7m, ri=\EM, rin=\E[%p1%dT, ritm=\E[23m, rmacs=\E(B,
        rmam=\E[?7l, rmcup=\E[?1049l\E[23;0;0t, rmir=\E[4l,
        rmkx=\E[?1l\E>, rmm=\E[?1034l, rmso=\E[27m, rmul=\E[24m,
        rs1=\Ec\E]104\007, rs2=\E[!p\E[?3;4l\E[4l\E>, sc=\E7,
        setab=\E[%?%p1%{8}%<%t4%p1%d%e%p1%{16}%<%t10%p1%{8}%-%d%e48;5;%p1%d%;m,
        setaf=\E[%?%p1%{8}%<%t3%p1%d%e%p1%{16}%<%t9%p1%{8}%-%d%e38;5;%p1%d%;m,
        sgr=%?%p9%t\E(0%e\E(B%;\E[0%?%p6%t;1%;%?%p5%t;2%;%?%p2%t;4%;%?%p1%p3%|%t;7%;%?%p4%t;5%;%?%p7%t;8%;m,
        sgr0=\E(B\E[m, sitm=\E[3m, smacs=\E(0, smam=\E[?7h,
        smcup=\E[?1049h\E[22;0;0t, smglp=\E[?69h\E[%i%p1%ds,
        smglr=\E[?69h\E[%i%p1%d;%p2%ds,
        smgrp=\E[?69h\E[%i;%p1%ds, smir=\E[4h, smkx=\E[?1h\E=,
        smm=\E[?1034h, smso=\E[7m, smul=\E[4m, tbc=\E[3g,
        u6=\E[%i%d;%dR, u7=\E[6n, u8=\E[?%[;0123456789]c,
        u9=\E[c, vpa=\E[%i%p1%dd,
    """)
