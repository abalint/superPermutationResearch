/* detach.c — Windows analogue of "nohup ... >>out 2>>err &" for a standard user.
 *
 * usage: detach.exe <workdir> <stdout-file> <stderr-file> <command> [args...]
 *
 * Launches <command> via CreateProcess with
 *   CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP |
 *   BELOW_NORMAL_PRIORITY_CLASS
 * so the child escapes the Windows OpenSSH session's job object (which has
 * KILL_ON_JOB_CLOSE) and survives ssh disconnect. stdout/stderr are opened in
 * APPEND mode on the given files; stdin comes from NUL. Working directory is
 * set to <workdir>. Command-line args are joined with single spaces, so paths
 * passed here must not contain spaces.
 *
 * Handle inheritance is restricted with PROC_THREAD_ATTRIBUTE_HANDLE_LIST to
 * exactly the three std handles — otherwise the child would also inherit the
 * sshd/PowerShell pipe handles and keep the ssh session open forever.
 *
 * prints: "pid <n>" on success (the pid of <command> itself), exit 0.
 * On failure prints "... err <n>" to stderr, exit 1.
 * If the job forbids breakaway (err 5) it retries once without breakaway.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static HANDLE open_append(const char *path, SECURITY_ATTRIBUTES *sa)
{
    return CreateFileA(path, FILE_APPEND_DATA,
                       FILE_SHARE_READ | FILE_SHARE_WRITE, sa,
                       OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
}

int main(int argc, char **argv)
{
    char cmd[8192] = "";
    int i;
    STARTUPINFOEXA six;
    PROCESS_INFORMATION pi;
    SECURITY_ATTRIBUTES sa;
    HANDLE handles[3];
    SIZE_T attrSize = 0;
    DWORD flags, err;
    BOOL ok;

    if (argc < 5) {
        fprintf(stderr, "usage: detach <workdir> <stdout-file> <stderr-file> <command> [args...]\n");
        return 2;
    }
    for (i = 4; i < argc; i++) {
        if (i > 4) strcat_s(cmd, sizeof cmd, " ");
        strcat_s(cmd, sizeof cmd, argv[i]);
    }

    sa.nLength = sizeof sa;
    sa.lpSecurityDescriptor = NULL;
    sa.bInheritHandle = TRUE;

    ZeroMemory(&six, sizeof six);
    six.StartupInfo.cb = sizeof six;
    six.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    six.StartupInfo.hStdInput  = CreateFileA("NUL", GENERIC_READ, FILE_SHARE_READ,
                                             &sa, OPEN_EXISTING, 0, NULL);
    six.StartupInfo.hStdOutput = open_append(argv[2], &sa);
    six.StartupInfo.hStdError  = open_append(argv[3], &sa);
    if (six.StartupInfo.hStdOutput == INVALID_HANDLE_VALUE ||
        six.StartupInfo.hStdError  == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "opening log file failed err %lu\n", (unsigned long)GetLastError());
        return 1;
    }

    /* Restrict inherited handles to exactly these three. */
    handles[0] = six.StartupInfo.hStdInput;
    handles[1] = six.StartupInfo.hStdOutput;
    handles[2] = six.StartupInfo.hStdError;
    InitializeProcThreadAttributeList(NULL, 1, 0, &attrSize);
    six.lpAttributeList = (LPPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(GetProcessHeap(), 0, attrSize);
    if (!six.lpAttributeList ||
        !InitializeProcThreadAttributeList(six.lpAttributeList, 1, 0, &attrSize) ||
        !UpdateProcThreadAttribute(six.lpAttributeList, 0,
                                   PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                   handles, sizeof handles, NULL, NULL)) {
        fprintf(stderr, "attribute list setup failed err %lu\n", (unsigned long)GetLastError());
        return 1;
    }

    flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_BREAKAWAY_FROM_JOB |
            DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP |
            BELOW_NORMAL_PRIORITY_CLASS;
    ok = CreateProcessA(NULL, cmd, NULL, NULL, TRUE, flags, NULL, argv[1],
                        &six.StartupInfo, &pi);
    if (!ok && GetLastError() == ERROR_ACCESS_DENIED) {
        fprintf(stderr, "breakaway denied (err 5); retrying without breakaway\n");
        flags &= ~CREATE_BREAKAWAY_FROM_JOB;
        ok = CreateProcessA(NULL, cmd, NULL, NULL, TRUE, flags, NULL, argv[1],
                            &six.StartupInfo, &pi);
    }
    if (!ok) {
        err = GetLastError();
        fprintf(stderr, "CreateProcess failed err %lu\n", (unsigned long)err);
        return 1;
    }
    printf("pid %lu\n", (unsigned long)pi.dwProcessId);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return 0;
}
